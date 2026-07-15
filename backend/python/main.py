import logging
import os
import asyncio
import time
import json
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logging.getLogger("httpx").setLevel(logging.WARNING)

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.api import router as api_router
from app.database import engine, Base
from app.services.admin_auth_service import token_secret_is_default
Base.metadata.create_all(bind=engine)


def ensure_content_management_schema() -> None:
    """Apply additive columns required by the current ORM models."""
    statements = (
        "ALTER TABLE ticket_products ADD COLUMN IF NOT EXISTS original_price DOUBLE PRECISION",
        "ALTER TABLE ticket_products ADD COLUMN IF NOT EXISTS valid_period VARCHAR(255)",
        "ALTER TABLE ticket_products ADD COLUMN IF NOT EXISTS sales_status VARCHAR(50) DEFAULT 'available'",
        "ALTER TABLE ticket_products ADD COLUMN IF NOT EXISTS purchase_url VARCHAR(500)",
        "ALTER TABLE ticket_products ADD COLUMN IF NOT EXISTS source_name VARCHAR(255)",
        "ALTER TABLE ticket_products ADD COLUMN IF NOT EXISTS source_type VARCHAR(50) DEFAULT 'manual'",
        "ALTER TABLE ticket_products ADD COLUMN IF NOT EXISTS use_policy TEXT",
        "ALTER TABLE ticket_products ADD COLUMN IF NOT EXISTS refund_policy TEXT",
        "ALTER TABLE ticket_products ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 100",
        "ALTER TABLE scenic_activities ADD COLUMN IF NOT EXISTS schedule_note VARCHAR(255)",
        "ALTER TABLE scenic_activities ADD COLUMN IF NOT EXISTS description TEXT",
        "ALTER TABLE scenic_activities ADD COLUMN IF NOT EXISTS detail TEXT",
        "ALTER TABLE scenic_activities ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'available'",
        "ALTER TABLE scenic_activities ADD COLUMN IF NOT EXISTS navigation_tips TEXT",
        "ALTER TABLE scenic_activities ADD COLUMN IF NOT EXISTS notice TEXT",
        "ALTER TABLE scenic_activities ADD COLUMN IF NOT EXISTS source_name VARCHAR(255)",
        "ALTER TABLE scenic_activities ADD COLUMN IF NOT EXISTS source_type VARCHAR(50) DEFAULT 'manual'",
        "ALTER TABLE scenic_activities ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 100",
    )
    try:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))
    except Exception:
        logging.getLogger(__name__).exception("Database schema compatibility migration failed")


ensure_content_management_schema()

app = FastAPI(
    title="AI数字人智慧景区导览系统",
    description="为游客提供智能导览服务，为管理员提供景区管理功能",
    version="1.0.0"
)

logger = logging.getLogger(__name__)

if token_secret_is_default():
    logger.warning("ADMIN_TOKEN_SECRET is not configured; using a development-only signing secret")


def _decode_request_body(raw_body: bytes):
    if not raw_body:
        return None
    try:
        return json.loads(raw_body)
    except Exception:
        return raw_body.decode("utf-8", errors="replace")


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    try:
        raw_body = await request.body()
        decoded_body = _decode_request_body(raw_body)
    except Exception:
        decoded_body = getattr(exc, "body", None)

    logger.warning(
        "Request validation failed: %s %s errors=%s body=%r",
        request.method,
        request.url.path,
        exc.errors(),
        decoded_body,
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


def _warmup_rag_models() -> None:
    from app.services.embedding_service import get_default_embedding_provider

    started_at = time.perf_counter()
    provider = get_default_embedding_provider()
    provider.embed_query("灵山胜境景区有哪些景点")

    from app.rag_config import get_rerank_enabled, get_rerank_batch_size, get_rerank_model_name
    if get_rerank_enabled():
        from app.services.rerank_service import get_cached_reranker

        reranker = get_cached_reranker(get_rerank_model_name(), get_rerank_batch_size())
        reranker.score("灵山胜境景点", ["灵山胜境景点介绍"])

    elapsed = time.perf_counter() - started_at
    logger.info("RAG models warmed up in %.2fs", elapsed)


@app.on_event("startup")
async def warmup_models_on_startup() -> None:
    enabled = os.getenv("RAG_WARMUP_ENABLED", "true").strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        return
    try:
        await asyncio.to_thread(_warmup_rag_models)
    except Exception:
        logger.exception("RAG model warmup failed; retrieval will retry lazily")

STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage", "guide-assets")
app.mount("/api/visitor/guide-assets", StaticFiles(directory=STORAGE_DIR), name="guide-assets")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "AI数字人智慧景区导览系统后端服务"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
