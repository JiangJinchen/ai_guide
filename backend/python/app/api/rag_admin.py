from threading import Lock

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel


router = APIRouter()
_state_lock = Lock()
_state = {
    "running": False,
    "status": "idle",
    "error": None,
    "steps": {},
}


class ReindexRequest(BaseModel):
    sync_chunks: bool = True
    sync_embeddings: bool = True
    build_faiss: bool = False
    model_name: str | None = None


@router.post("/reindex", status_code=202)
async def start_reindex(
    request: ReindexRequest,
    background_tasks: BackgroundTasks,
):
    with _state_lock:
        if _state["running"]:
            raise HTTPException(status_code=409, detail="RAG reindex is already running")
        _state.update({
            "running": True,
            "status": "queued",
            "error": None,
            "steps": {},
        })

    background_tasks.add_task(_run_reindex, request)
    return get_reindex_status()


@router.get("/reindex/status")
async def reindex_status():
    return get_reindex_status()


def get_reindex_status() -> dict:
    with _state_lock:
        return dict(_state)


def _run_reindex(request: ReindexRequest) -> None:
    from app.database import SessionLocal, engine
    from app.models import KnowledgeChunk, KnowledgeChunkEmbedding
    from app.rag_config import get_embedding_model_name
    from app.services.chunk_service import sync_chunks_from_database
    from app.services.embedding_service import (
        SentenceTransformerEmbeddingProvider,
        sync_embeddings_from_database,
    )
    from app.services.faiss_index_service import build_faiss_index

    db = SessionLocal()
    try:
        _set_state(status="running")
        KnowledgeChunk.__table__.create(bind=engine, checkfirst=True)
        if request.sync_embeddings or request.build_faiss:
            KnowledgeChunkEmbedding.__table__.create(bind=engine, checkfirst=True)

        if request.sync_chunks:
            stats = sync_chunks_from_database(db)
            _set_step("sync_chunks", stats.to_dict())

        model_name = request.model_name or get_embedding_model_name()
        if request.sync_embeddings:
            provider = SentenceTransformerEmbeddingProvider(model_name=model_name)
            stats = sync_embeddings_from_database(db, provider=provider)
            _set_step("sync_embeddings", stats.to_dict())

        if request.build_faiss:
            stats = build_faiss_index(db, model_name=model_name)
            _set_step("build_faiss", stats.to_dict())
        _set_state(status="completed")
    except Exception as exc:
        db.rollback()
        _set_state(status="failed", error=str(exc))
    finally:
        db.close()
        _set_state(running=False)


def _set_step(name: str, value: dict) -> None:
    with _state_lock:
        _state["steps"][name] = value


def _set_state(**updates) -> None:
    with _state_lock:
        _state.update(updates)
