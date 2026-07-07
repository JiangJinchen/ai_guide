from fastapi import APIRouter
from app.api import visitor, admin, ai

router = APIRouter()

router.include_router(visitor.router, prefix="/visitor", tags=["visitor"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
router.include_router(ai.router, prefix="/ai", tags=["ai"])