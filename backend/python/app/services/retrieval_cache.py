from collections import OrderedDict
from copy import deepcopy
from threading import RLock
import time

from app.rag_config import (
    get_adjacent_chunk_window,
    get_cache_enabled,
    get_cache_max_entries,
    get_cache_ttl_seconds,
    get_context_max_chunks,
    get_context_max_tokens,
    get_embedding_model_name,
    get_min_confidence,
    get_postprocess_enabled,
    get_rerank_enabled,
    get_rerank_candidate_count,
    get_rerank_model_name,
    get_semantic_min_score,
    get_vector_backend,
)


_CACHE = OrderedDict()
_LOCK = RLock()
_HITS = 0
_MISSES = 0


def build_cache_key(mode: str, query: str, top_k: int) -> tuple:
    return (
        mode,
        (query or "").strip().lower(),
        top_k,
        get_embedding_model_name(),
        get_vector_backend(),
        get_semantic_min_score(),
        get_rerank_enabled(),
        get_rerank_model_name() if get_rerank_enabled() else "",
        get_rerank_candidate_count() if get_rerank_enabled() else 0,
        get_postprocess_enabled(),
        get_min_confidence(),
        get_adjacent_chunk_window(),
        get_context_max_chunks(),
        get_context_max_tokens(),
    )


def get_cached_results(key: tuple) -> tuple[bool, list[dict] | None]:
    global _HITS, _MISSES
    if not get_cache_enabled():
        return False, None
    now = time.monotonic()
    with _LOCK:
        cached = _CACHE.get(key)
        if cached is None:
            _MISSES += 1
            return False, None
        expires_at, value = cached
        if expires_at <= now:
            _CACHE.pop(key, None)
            _MISSES += 1
            return False, None
        _CACHE.move_to_end(key)
        _HITS += 1
        return True, deepcopy(value)


def set_cached_results(key: tuple, results: list[dict]) -> None:
    if not get_cache_enabled():
        return
    expires_at = time.monotonic() + get_cache_ttl_seconds()
    max_entries = get_cache_max_entries()
    with _LOCK:
        _CACHE[key] = (expires_at, deepcopy(results))
        _CACHE.move_to_end(key)
        while len(_CACHE) > max_entries:
            _CACHE.popitem(last=False)


def clear_retrieval_cache() -> None:
    global _HITS, _MISSES
    with _LOCK:
        _CACHE.clear()
        _HITS = 0
        _MISSES = 0


def get_cache_status() -> dict:
    with _LOCK:
        return {
            "enabled": get_cache_enabled(),
            "entries": len(_CACHE),
            "hits": _HITS,
            "misses": _MISSES,
            "ttl_seconds": get_cache_ttl_seconds(),
            "max_entries": get_cache_max_entries(),
        }
