import os


RAG_MODE_LEGACY = "legacy"
RAG_MODE_CHUNK = "chunk"
RAG_MODE_HYBRID = "hybrid"
RAG_MODE_SEMANTIC = "semantic"

SUPPORTED_RAG_MODES = {
    RAG_MODE_LEGACY,
    RAG_MODE_CHUNK,
    RAG_MODE_HYBRID,
    RAG_MODE_SEMANTIC,
}


def get_rag_mode() -> str:
    mode = os.getenv("RAG_MODE", RAG_MODE_LEGACY).strip().lower()
    if mode not in SUPPORTED_RAG_MODES:
        return RAG_MODE_LEGACY
    return mode


def get_chunk_size() -> int:
    return _get_bounded_int("RAG_CHUNK_SIZE", default=500, minimum=200, maximum=2000)


def get_chunk_overlap() -> int:
    chunk_size = get_chunk_size()
    return _get_bounded_int(
        "RAG_CHUNK_OVERLAP",
        default=80,
        minimum=0,
        maximum=max(0, chunk_size // 2),
    )


def get_embedding_model_name() -> str:
    return os.getenv(
        "RAG_EMBEDDING_MODEL",
        "BAAI/bge-small-zh-v1.5",
    ).strip()


def get_embedding_device() -> str:
    return os.getenv("RAG_EMBEDDING_DEVICE", "cpu").strip()


def get_embedding_batch_size() -> int:
    return _get_bounded_int(
        "RAG_EMBEDDING_BATCH_SIZE",
        default=32,
        minimum=1,
        maximum=256,
    )


def get_semantic_min_score() -> float:
    return _get_bounded_float(
        "RAG_SEMANTIC_MIN_SCORE",
        default=0.35,
        minimum=-1.0,
        maximum=1.0,
    )


def get_hybrid_rrf_k() -> int:
    return _get_bounded_int("RAG_HYBRID_RRF_K", default=60, minimum=1, maximum=200)


def get_query_prefix() -> str:
    return os.getenv(
        "RAG_QUERY_PREFIX",
        "\u4e3a\u8fd9\u4e2a\u53e5\u5b50\u751f\u6210\u8868\u793a\u4ee5\u7528\u4e8e\u68c0\u7d22\u76f8\u5173\u6587\u7ae0\uff1a",
    )


def get_postprocess_enabled() -> bool:
    return _get_bool("RAG_POSTPROCESS_ENABLED", default=True)


def get_min_confidence() -> float:
    return _get_bounded_float(
        "RAG_MIN_CONFIDENCE",
        default=0.20,
        minimum=0.0,
        maximum=1.0,
    )


def get_keyword_score_scale() -> float:
    return _get_bounded_float(
        "RAG_KEYWORD_SCORE_SCALE",
        default=8.0,
        minimum=1.0,
        maximum=100.0,
    )


def get_adjacent_chunk_window() -> int:
    return _get_bounded_int(
        "RAG_ADJACENT_CHUNK_WINDOW",
        default=1,
        minimum=0,
        maximum=3,
    )


def get_context_max_chunks() -> int:
    return _get_bounded_int(
        "RAG_CONTEXT_MAX_CHUNKS",
        default=6,
        minimum=1,
        maximum=30,
    )


def get_context_max_tokens() -> int:
    return _get_bounded_int(
        "RAG_CONTEXT_MAX_TOKENS",
        default=1800,
        minimum=100,
        maximum=16000,
    )


def get_vector_backend() -> str:
    backend = os.getenv("RAG_VECTOR_BACKEND", "exact").strip().lower()
    return backend if backend in {"exact", "faiss"} else "exact"


def get_faiss_directory() -> str:
    return os.getenv("RAG_FAISS_DIR", "").strip()


def get_cache_enabled() -> bool:
    return _get_bool("RAG_CACHE_ENABLED", default=True)


def get_cache_ttl_seconds() -> int:
    return _get_bounded_int(
        "RAG_CACHE_TTL_SECONDS",
        default=60,
        minimum=1,
        maximum=3600,
    )


def get_cache_max_entries() -> int:
    return _get_bounded_int(
        "RAG_CACHE_MAX_ENTRIES",
        default=256,
        minimum=1,
        maximum=10000,
    )


def get_rerank_enabled() -> bool:
    return _get_bool("RAG_RERANK_ENABLED", default=True)


def get_rerank_model_name() -> str:
    return os.getenv(
        "RAG_RERANK_MODEL",
        "BAAI/bge-reranker-base",
    ).strip()


def get_rerank_candidate_count() -> int:
    return _get_bounded_int(
        "RAG_RERANK_CANDIDATES",
        default=12,
        minimum=3,
        maximum=100,
    )


def get_rerank_batch_size() -> int:
    return _get_bounded_int(
        "RAG_RERANK_BATCH_SIZE",
        default=16,
        minimum=1,
        maximum=128,
    )


def _get_bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(minimum, min(value, maximum))


def _get_bounded_float(
    name: str,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(minimum, min(value, maximum))


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
