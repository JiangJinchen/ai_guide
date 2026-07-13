from dataclasses import asdict, dataclass
from functools import lru_cache
import json
import logging
import math

from sqlalchemy.orm import Session

from app.models import KnowledgeChunk, KnowledgeChunkEmbedding
from app.services.retrieval_cache import clear_retrieval_cache
from app.rag_config import (
    get_embedding_batch_size,
    get_embedding_device,
    get_embedding_model_name,
    get_query_prefix,
    get_semantic_min_score,
    get_vector_backend,
)


logger = logging.getLogger(__name__)


@dataclass
class EmbeddingSyncStats:
    model_name: str
    chunks: int = 0
    created: int = 0
    updated: int = 0
    deleted: int = 0
    unchanged: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


class SentenceTransformerEmbeddingProvider:
    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        batch_size: int | None = None,
        query_prefix: str | None = None,
    ):
        self.model_name = model_name or get_embedding_model_name()
        self.device = device or get_embedding_device()
        self.batch_size = batch_size or get_embedding_batch_size()
        self.query_prefix = get_query_prefix() if query_prefix is None else query_prefix
        self._model = None

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._encode([f"{self.query_prefix}{text}"])[0]

    def _encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is required for semantic retrieval"
                ) from exc
            self._model = SentenceTransformer(self.model_name, device=self.device)

        vectors = self._model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return [vector.tolist() for vector in vectors]


@lru_cache(maxsize=2)
def _cached_default_provider(
    model_name: str,
    device: str,
    batch_size: int,
    query_prefix: str,
) -> SentenceTransformerEmbeddingProvider:
    return SentenceTransformerEmbeddingProvider(
        model_name=model_name,
        device=device,
        batch_size=batch_size,
        query_prefix=query_prefix,
    )


def get_default_embedding_provider() -> SentenceTransformerEmbeddingProvider:
    return _cached_default_provider(
        get_embedding_model_name(),
        get_embedding_device(),
        get_embedding_batch_size(),
        get_query_prefix(),
    )


def sync_embeddings_from_database(
    db: Session,
    provider=None,
    commit: bool = True,
) -> EmbeddingSyncStats:
    provider = provider or get_default_embedding_provider()
    model_name = provider.model_name
    chunks = db.query(KnowledgeChunk).order_by(KnowledgeChunk.id.asc()).all()
    existing_rows = db.query(KnowledgeChunkEmbedding).filter(
        KnowledgeChunkEmbedding.model_name == model_name
    ).all()
    existing_by_chunk_id = {row.chunk_id: row for row in existing_rows}
    chunk_ids = {chunk.id for chunk in chunks}
    stats = EmbeddingSyncStats(model_name=model_name, chunks=len(chunks))

    stale_chunks = [
        chunk
        for chunk in chunks
        if chunk.id not in existing_by_chunk_id
        or existing_by_chunk_id[chunk.id].content_hash != chunk.content_hash
    ]
    vectors_by_chunk_id: dict[int, list[float]] = {}
    batch_size = max(1, int(getattr(provider, "batch_size", 32)))
    dimensions = None

    for index in range(0, len(stale_chunks), batch_size):
        batch = stale_chunks[index:index + batch_size]
        vectors = provider.embed_documents([chunk.content for chunk in batch])
        if len(vectors) != len(batch):
            raise ValueError("embedding provider returned an unexpected vector count")
        for chunk, vector in zip(batch, vectors):
            normalized = normalize_vector(vector)
            if dimensions is None:
                dimensions = len(normalized)
            elif len(normalized) != dimensions:
                raise ValueError("embedding provider returned inconsistent dimensions")
            vectors_by_chunk_id[chunk.id] = normalized

    for chunk in chunks:
        existing = existing_by_chunk_id.get(chunk.id)
        vector = vectors_by_chunk_id.get(chunk.id)
        if vector is None:
            stats.unchanged += 1
            continue

        embedding_json = json.dumps(vector, separators=(",", ":"))
        if existing is None:
            db.add(
                KnowledgeChunkEmbedding(
                    chunk_id=chunk.id,
                    model_name=model_name,
                    content_hash=chunk.content_hash,
                    dimensions=len(vector),
                    embedding_json=embedding_json,
                )
            )
            stats.created += 1
        else:
            existing.content_hash = chunk.content_hash
            existing.dimensions = len(vector)
            existing.embedding_json = embedding_json
            stats.updated += 1

    for row in existing_rows:
        if row.chunk_id not in chunk_ids:
            db.delete(row)
            stats.deleted += 1

    if commit:
        db.commit()
    else:
        db.flush()
    clear_retrieval_cache()
    return stats


def search_semantic_chunks(
    db: Session,
    query: str,
    top_k: int = 3,
    provider=None,
    min_score: float | None = None,
) -> list[dict]:
    query = (query or "").strip()
    if not query or top_k <= 0:
        return []

    provider = provider or get_default_embedding_provider()
    threshold = get_semantic_min_score() if min_score is None else min_score
    if get_vector_backend() == "faiss":
        query_vector = normalize_vector(provider.embed_query(query))
        try:
            return _search_semantic_faiss(
                db,
                query_vector,
                provider.model_name,
                threshold,
                top_k,
            )
        except Exception as exc:
            logger.warning(
                "FAISS retrieval unavailable; using exact cosine search: %s",
                exc,
            )
            return _search_semantic_exact(
                db,
                query,
                provider,
                threshold,
                top_k,
                query_vector=query_vector,
            )
    return _search_semantic_exact(db, query, provider, threshold, top_k)


def _search_semantic_exact(
    db: Session,
    query: str,
    provider,
    threshold: float,
    top_k: int,
    query_vector=None,
) -> list[dict]:
    rows = (
        db.query(KnowledgeChunk, KnowledgeChunkEmbedding)
        .join(
            KnowledgeChunkEmbedding,
            KnowledgeChunkEmbedding.chunk_id == KnowledgeChunk.id,
        )
        .filter(KnowledgeChunkEmbedding.model_name == provider.model_name)
        .all()
    )
    rows = [
        (chunk, embedding)
        for chunk, embedding in rows
        if embedding.content_hash == chunk.content_hash
    ]
    if not rows:
        raise RuntimeError(
            f"no current embeddings are available for model '{provider.model_name}'"
        )
    if query_vector is None:
        query_vector = normalize_vector(provider.embed_query(query))

    results = []
    for chunk, embedding in rows:
        vector = json.loads(embedding.embedding_json)
        if len(vector) != embedding.dimensions:
            continue
        score = cosine_similarity(query_vector, vector)
        if score < threshold:
            continue
        results.append(_semantic_result(chunk, score, vector_backend="exact"))

    return sorted(
        results,
        key=lambda item: item["semantic_score"],
        reverse=True,
    )[:top_k]


def _search_semantic_faiss(
    db: Session,
    query_vector,
    model_name: str,
    threshold: float,
    top_k: int,
) -> list[dict]:
    from app.services.faiss_index_service import search_faiss_index

    candidates = search_faiss_index(
        query_vector,
        model_name=model_name,
        top_k=max(20, top_k * 4),
    )
    chunk_ids = [chunk_id for chunk_id, _, _ in candidates]
    chunks = db.query(KnowledgeChunk).filter(KnowledgeChunk.id.in_(chunk_ids)).all()
    chunks_by_id = {chunk.id: chunk for chunk in chunks}
    results = []
    for chunk_id, content_hash, score in candidates:
        chunk = chunks_by_id.get(chunk_id)
        if chunk is None or chunk.content_hash != content_hash or score < threshold:
            continue
        results.append(_semantic_result(chunk, score, vector_backend="faiss"))
        if len(results) >= top_k:
            break
    return results


def _semantic_result(chunk: KnowledgeChunk, score: float, vector_backend: str) -> dict:
    score = round(float(score), 6)
    return {
        "content": chunk.content,
        "score": score,
        "semantic_score": score,
        "source_type": chunk.source_type,
        "source_id": chunk.source_id,
        "chunk_index": chunk.chunk_index,
        "title": chunk.title,
        "retrieval_mode": "semantic",
        "vector_backend": vector_backend,
    }


def normalize_vector(vector) -> list[float]:
    values = [float(value) for value in vector]
    if not values or not all(math.isfinite(value) for value in values):
        raise ValueError("embedding vector must contain finite values")
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        raise ValueError("embedding vector norm must be positive")
    return [value / norm for value in values]


def cosine_similarity(left, right) -> float:
    left_values = normalize_vector(left)
    right_values = normalize_vector(right)
    if len(left_values) != len(right_values):
        raise ValueError("embedding dimensions do not match")
    return sum(a * b for a, b in zip(left_values, right_values))
