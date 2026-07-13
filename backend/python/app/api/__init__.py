from fastapi import APIRouter
from app.api import visitor, admin, ai, rag_admin

router = APIRouter()

router.include_router(visitor.router, prefix="/visitor", tags=["visitor"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
router.include_router(ai.router, prefix="/ai", tags=["ai"])
router.include_router(rag_admin.router, prefix="/admin/rag", tags=["admin-rag"])
