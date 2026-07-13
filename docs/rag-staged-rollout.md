# RAG staged rollout

The retrieval path is introduced behind `RAG_MODE` so each phase can be
enabled or rolled back independently.

| Mode | Purpose | Current status |
| --- | --- | --- |
| `legacy` | Existing full-row keyword scoring | Active and default |
| `chunk` | Chunk-level keyword retrieval | Active after explicit opt-in |
| `hybrid` | Keyword and semantic recall with RRF | Active after embedding sync |
| `semantic` | Embedding cosine-similarity retrieval | Active after embedding sync |

## Phase 0: switch and fallback

- Keep `RAG_MODE=legacy` in production.
- Invalid or not-yet-active modes fall back to legacy retrieval.
- `/api/ai/inference` and `/api/ai/rag` keep their existing contracts.

Rollback: set `RAG_MODE=legacy` and restart the Python service.

## Phase 1: chunk data preparation

Create and synchronize chunks without changing online retrieval:

```powershell
cd backend/python
python manage_rag.py sync-chunks
python manage_rag.py status
```

Defaults are 500 characters per core chunk and 80 characters of overlap.
They can be changed with `RAG_CHUNK_SIZE` and `RAG_CHUNK_OVERLAP`, or with
the command options `--chunk-size` and `--overlap`.

Synchronization is idempotent. It updates changed chunks and removes stale
chunks for deleted or shortened `knowledge` and `spot` sources.

Rollback: keep `RAG_MODE=legacy`. The `knowledge_chunks` table is isolated and
can remain in place without affecting requests.

## Phase 2: chunk keyword retrieval

Phase 2 is implemented behind `RAG_MODE=chunk`. It retrieves candidate chunks
from `knowledge_chunks` and applies the existing keyword and two-character
fragment scoring to the smaller units. Results include source metadata, while
the AI endpoints keep their existing document and score response shape.

Before enabling it, build the chunk table and synchronize data:

```powershell
cd backend/python
python manage_rag.py sync-chunks
```

Enable it with `RAG_MODE=chunk` and restart the Python service. If the chunk
table is missing or retrieval raises an error, the service logs the failure and
falls back to legacy retrieval for that request.

When `RAG_MODE=chunk`, retrieval is still lexical only. Candidate filtering
relies on text matching. Phase 4 post-processing can still calibrate these
keyword hits and stitch their neighboring chunks.

Rollback: set `RAG_MODE=legacy` and restart the Python service. The chunk table
and synchronized data can remain in place.

## Phase 3: semantic and hybrid retrieval

Phase 3 stores embeddings in the separate `knowledge_chunk_embeddings` table.
Each row is tied to a chunk content hash and embedding model, so changed chunks
are re-embedded incrementally and different models can coexist.

Install the embedding dependency and build vectors after chunk synchronization:

```powershell
cd backend/python
pip install -r requirements.txt
python manage_rag.py sync-chunks
python manage_rag.py sync-embeddings
python manage_rag.py embedding-status
```

The default model is `BAAI/bge-small-zh-v1.5` on CPU. The first embedding sync
may download the model. Configuration variables are:

- `RAG_EMBEDDING_MODEL`: sentence-transformers model name.
- `RAG_EMBEDDING_DEVICE`: defaults to `cpu`.
- `RAG_EMBEDDING_BATCH_SIZE`: defaults to `32`.
- `RAG_SEMANTIC_MIN_SCORE`: cosine threshold, defaults to `0.35`.
- `RAG_HYBRID_RRF_K`: reciprocal-rank-fusion constant, defaults to `60`.
- `RAG_QUERY_PREFIX`: optional retrieval instruction for query embeddings.

Select the online mode with exactly one of:

```powershell
$env:RAG_MODE = "semantic"
$env:RAG_MODE = "hybrid"
```

`semantic` ranks current-model embeddings by cosine similarity. `hybrid`
retrieves a wider keyword and semantic candidate set, then combines their ranks
with reciprocal rank fusion instead of adding incompatible raw scores.

Fallback behavior is staged:

1. In `hybrid`, an unavailable embedding model degrades to chunk retrieval.
2. If hybrid or chunk retrieval fails, the request falls back to legacy.
3. In `semantic`, an embedding or semantic-query failure falls back to legacy.

The current vector store uses JSON vectors in PostgreSQL and exact cosine
scanning. This is real semantic retrieval and is suitable for a small knowledge
base, but it is not an approximate-nearest-neighbor index. A pgvector, FAISS, or
similar ANN backend belongs in the performance phase once quality is measured.

Rollback: set `RAG_MODE=chunk` to retain chunk retrieval, or `RAG_MODE=legacy`
to bypass all staged RAG data. Embedding rows can remain in place.

## Phase 4: confidence, stitching, and context budget

Phase 4 post-processes results from `chunk`, `semantic`, and `hybrid` modes.
Legacy retrieval is unchanged. Post-processing is enabled by default and can be
disabled independently with `RAG_POSTPROCESS_ENABLED=false`.

The post-processor performs three operations:

1. It maps lexical scores and semantic cosine scores separately into a `0..1`
   confidence range. Hybrid confidence combines both signals and adds a small
   agreement bonus.
2. It loads neighboring chunks from the same source, merges them in source
   order, and removes repeated overlap text.
3. It limits the final context by result count, chunk count, and an approximate
   mixed Chinese/Latin token budget.

The confidence value is a tunable retrieval score, not a statistical
probability. Its purpose is thresholding and comparison during evaluation.

Configuration variables are:

- `RAG_POSTPROCESS_ENABLED`: defaults to `true`.
- `RAG_MIN_CONFIDENCE`: defaults to `0.20`.
- `RAG_KEYWORD_SCORE_SCALE`: defaults to `8.0`.
- `RAG_ADJACENT_CHUNK_WINDOW`: defaults to `1`, with a maximum of `3`.
- `RAG_CONTEXT_MAX_CHUNKS`: defaults to `6`.
- `RAG_CONTEXT_MAX_TOKENS`: defaults to `1800`.

Processed results include `confidence`, `chunk_indices`,
`matched_chunk_indices`, `stitched`, `context_truncated`, and
`context_token_estimate` for tracing.
The existing AI endpoint document and score response shape remains compatible.

The token estimator counts each CJK character as roughly one token and Latin
text as roughly four characters per token. This avoids another runtime
dependency and is intended as a conservative context guard, not exact billing.

Rollback: keep `RAG_MODE=hybrid` and set `RAG_POSTPROCESS_ENABLED=false` to use
raw phase 3 results. Switching to `chunk` or `legacy` remains available.

## Phase 5: performance, reranking, async rebuild, and evaluation

Phase 5 is implemented as optional operational capabilities around the stable
retrieval path.

### ANN index

The default vector backend remains exact cosine scanning. To build and use an
optional FAISS index:

```powershell
cd backend/python
pip install -r requirements-rag-ann.txt
python manage_rag.py build-faiss
python manage_rag.py faiss-status
$env:RAG_VECTOR_BACKEND = "faiss"
```

The index is stored under `data/faiss/` by model fingerprint and carries the
chunk content hashes used to validate each hit. If FAISS is not installed, the
index is missing, or metadata is stale, semantic retrieval automatically falls
back to exact cosine search.

### Cache and rerank

The process-local TTL cache is enabled by default. It is invalidated by chunk,
embedding, and FAISS rebuilds, and also expires to handle changes made by other
processes. Main settings are:

- `RAG_CACHE_ENABLED`: defaults to `true`.
- `RAG_CACHE_TTL_SECONDS`: defaults to `60`.
- `RAG_CACHE_MAX_ENTRIES`: defaults to `256`.

CrossEncoder reranking is opt-in because its model is larger and slower:

```powershell
$env:RAG_RERANK_ENABLED = "true"
$env:RAG_RERANK_MODEL = "BAAI/bge-reranker-base"
```

The service recalls up to `RAG_RERANK_CANDIDATES` results, reranks them, then
applies Phase 4 confidence and context processing. Rerank failure keeps the
original recall order. The model is loaded lazily, so the default path does not
require the reranker model.

### Async rebuild

The admin API provides a background rebuild task:

```text
POST /api/admin/rag/reindex
GET  /api/admin/rag/reindex/status
```

The request can select `sync_chunks`, `sync_embeddings`, `build_faiss`, and an
optional `model_name`. A second rebuild request is rejected while one is
running. Errors are retained in the status response and do not change the
online retrieval mode.

### Evaluation gate

Create a UTF-8 JSONL file with one case per line:

```json
{"query":"opening hours","expected":[{"source_type":"knowledge","source_id":1}]}
{"query":"history","expected":[{"source_type":"knowledge","source_id":2,"chunk_index":0}]}
```

Run an evaluation gate before changing the online mode:

```powershell
python manage_rag.py evaluate-rag `
  --dataset docs/rag-eval.jsonl `
  --mode hybrid `
  --top-k 3 `
  --min-hit-rate 0.80 `
  --min-mrr 0.60
```

The command reports hit rate, MRR, average latency, and exits with code `1`
when either threshold is not met. This makes quality regression a deployment
condition instead of relying only on manual queries.

Rollback: set `RAG_VECTOR_BACKEND=exact`,
`RAG_RERANK_ENABLED=false`, and `RAG_POSTPROCESS_ENABLED=false` to remove the
optional performance layers while retaining hybrid retrieval. Setting
`RAG_MODE=legacy` bypasses all staged RAG behavior.

There are no required later phases. Future improvements can replace the
process-local cache with a shared cache, move rebuilds to a durable job queue,
or add a stronger reranker after evaluation data justifies the cost.

1. Phase 5 adds ANN indexing, caching, asynchronous indexing, reranking, and evaluation gates.
