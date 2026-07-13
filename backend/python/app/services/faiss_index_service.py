from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from threading import RLock

from app.rag_config import get_faiss_directory
from app.services.retrieval_cache import clear_retrieval_cache


_INDEX_CACHE = {}
_INDEX_CACHE_LOCK = RLock()


@dataclass
class FaissBuildStats:
    model_name: str
    vectors: int
    dimensions: int
    index_path: str
    metadata_path: str

    def to_dict(self) -> dict:
        return asdict(self)


def build_faiss_index(
    db,
    model_name: str,
) -> FaissBuildStats:
    from app.models import KnowledgeChunk, KnowledgeChunkEmbedding
    from app.services.embedding_service import normalize_vector

    faiss, numpy = _load_faiss_dependencies()
    rows = (
        db.query(KnowledgeChunk, KnowledgeChunkEmbedding)
        .join(
            KnowledgeChunkEmbedding,
            KnowledgeChunkEmbedding.chunk_id == KnowledgeChunk.id,
        )
        .filter(KnowledgeChunkEmbedding.model_name == model_name)
        .order_by(KnowledgeChunk.id.asc())
        .all()
    )
    rows = [
        (chunk, embedding)
        for chunk, embedding in rows
        if chunk.content_hash == embedding.content_hash
    ]
    if not rows:
        raise RuntimeError(f"no current embeddings are available for model '{model_name}'")

    vectors = []
    metadata_rows = []
    dimensions = None
    for chunk, embedding in rows:
        vector = normalize_vector(json.loads(embedding.embedding_json))
        if dimensions is None:
            dimensions = len(vector)
        elif len(vector) != dimensions:
            raise ValueError("embedding dimensions are inconsistent")
        vectors.append(vector)
        metadata_rows.append({
            "chunk_id": chunk.id,
            "content_hash": chunk.content_hash,
        })

    matrix = numpy.asarray(vectors, dtype="float32")
    index = faiss.IndexFlatIP(dimensions)
    index.add(matrix)
    index_path, metadata_path = get_faiss_paths(model_name)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    temp_index = index_path.with_suffix(index_path.suffix + ".tmp")
    temp_metadata = metadata_path.with_suffix(metadata_path.suffix + ".tmp")

    faiss.write_index(index, str(temp_index))
    metadata = {
        "version": 1,
        "model_name": model_name,
        "dimensions": dimensions,
        "vectors": len(metadata_rows),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rows": metadata_rows,
    }
    with temp_metadata.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(metadata, handle, ensure_ascii=True, separators=(",", ":"))
    os.replace(temp_index, index_path)
    os.replace(temp_metadata, metadata_path)
    invalidate_faiss_cache(model_name)
    clear_retrieval_cache()
    return FaissBuildStats(
        model_name=model_name,
        vectors=len(metadata_rows),
        dimensions=dimensions,
        index_path=str(index_path),
        metadata_path=str(metadata_path),
    )


def search_faiss_index(
    query_vector,
    model_name: str,
    top_k: int,
) -> list[tuple[int, str, float]]:
    if top_k <= 0:
        return []
    _, numpy = _load_faiss_dependencies()
    from app.services.embedding_service import normalize_vector
    index, metadata = _load_cached_index(model_name)
    vector = normalize_vector(query_vector)
    if len(vector) != metadata["dimensions"]:
        raise ValueError("query embedding dimensions do not match the FAISS index")

    query_matrix = numpy.asarray([vector], dtype="float32")
    limit = min(top_k, metadata["vectors"])
    scores, positions = index.search(query_matrix, limit)
    results = []
    for score, position in zip(scores[0], positions[0]):
        if position < 0:
            continue
        row = metadata["rows"][int(position)]
        results.append((row["chunk_id"], row["content_hash"], float(score)))
    return results


def get_faiss_status(model_name: str) -> dict:
    index_path, metadata_path = get_faiss_paths(model_name)
    if not index_path.exists() or not metadata_path.exists():
        return {
            "model_name": model_name,
            "ready": False,
            "index_path": str(index_path),
            "metadata_path": str(metadata_path),
        }
    with metadata_path.open("r", encoding="utf-8") as handle:
        metadata = json.load(handle)
    return {
        "model_name": model_name,
        "ready": True,
        "vectors": metadata.get("vectors", 0),
        "dimensions": metadata.get("dimensions", 0),
        "generated_at": metadata.get("generated_at"),
        "index_path": str(index_path),
        "metadata_path": str(metadata_path),
    }


def get_faiss_paths(model_name: str) -> tuple[Path, Path]:
    configured = get_faiss_directory()
    base_directory = (
        Path(configured).expanduser().resolve()
        if configured
        else Path(__file__).resolve().parents[4] / "data" / "faiss"
    )
    model_key = hashlib.sha256(model_name.encode("utf-8")).hexdigest()[:16]
    return (
        base_directory / f"{model_key}.faiss",
        base_directory / f"{model_key}.json",
    )


def invalidate_faiss_cache(model_name: str | None = None) -> None:
    with _INDEX_CACHE_LOCK:
        if model_name is None:
            _INDEX_CACHE.clear()
        else:
            _INDEX_CACHE.pop(model_name, None)


def _load_cached_index(model_name: str):
    faiss, _ = _load_faiss_dependencies()
    index_path, metadata_path = get_faiss_paths(model_name)
    if not index_path.exists() or not metadata_path.exists():
        raise RuntimeError(f"FAISS index is not ready for model '{model_name}'")
    signature = (index_path.stat().st_mtime_ns, metadata_path.stat().st_mtime_ns)

    with _INDEX_CACHE_LOCK:
        cached = _INDEX_CACHE.get(model_name)
        if cached and cached[0] == signature:
            return cached[1], cached[2]

        with metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)
        index = faiss.read_index(str(index_path))
        if metadata.get("model_name") != model_name:
            raise ValueError("FAISS metadata model does not match the requested model")
        if index.ntotal != metadata.get("vectors"):
            raise ValueError("FAISS index and metadata vector counts do not match")
        _INDEX_CACHE[model_name] = (signature, index, metadata)
        return index, metadata


def _load_faiss_dependencies():
    try:
        import faiss
        import numpy
    except ImportError as exc:
        raise RuntimeError(
            "faiss-cpu and numpy are required for the FAISS vector backend"
        ) from exc
    return faiss, numpy
