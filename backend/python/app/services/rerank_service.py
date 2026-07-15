import math
from functools import lru_cache

from app.rag_config import (
    get_rerank_batch_size,
    get_rerank_model_name,
)


class CrossEncoderReranker:
    def __init__(
        self,
        model_name: str | None = None,
        batch_size: int | None = None,
    ):
        self.model_name = model_name or get_rerank_model_name()
        self.batch_size = batch_size or get_rerank_batch_size()
        self._model = None
        self._load_error = None

    def score(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        if self._load_error is not None:
            raise RuntimeError(self._load_error)
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name)
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is required for CrossEncoder reranking"
                ) from exc
            except Exception as exc:
                self._load_error = f"failed to load reranker '{self.model_name}': {exc}"
                raise RuntimeError(self._load_error) from exc
        scores = self._model.predict(
            [(query, document) for document in documents],
            batch_size=self.batch_size,
            show_progress_bar=False,
        )
        return [float(score) for score in scores]


@lru_cache(maxsize=2)
def get_cached_reranker(model_name: str, batch_size: int) -> CrossEncoderReranker:
    return CrossEncoderReranker(model_name=model_name, batch_size=batch_size)


def rerank_results(
    query: str,
    results: list[dict],
    top_k: int,
    reranker=None,
) -> list[dict]:
    if not results or top_k <= 0:
        return []
    if reranker is None:
        from app.rag_config import get_rerank_batch_size, get_rerank_model_name

        reranker = get_cached_reranker(
            get_rerank_model_name(),
            get_rerank_batch_size(),
        )
    scores = reranker.score(query, [item.get("content", "") for item in results])
    if len(scores) != len(results):
        raise ValueError("reranker returned an unexpected score count")

    reranked = []
    for source_result, score in zip(results, scores):
        result = dict(source_result)
        result["rerank_score"] = score
        result["rerank_confidence"] = _sigmoid(score)
        result["rerank_model"] = reranker.model_name
        reranked.append(result)
    return sorted(
        reranked,
        key=lambda item: item["rerank_score"],
        reverse=True,
    )[:top_k]


def _sigmoid(value: float) -> float:
    value = max(-60.0, min(60.0, float(value)))
    return 1.0 / (1.0 + math.exp(-value))
