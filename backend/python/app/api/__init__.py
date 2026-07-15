from fastapi import APIRouter, Depends
from app.admin_auth import require_admin_access
from app.api import visitor, admin, ai, rag_admin, analytics, auth, visitor_auth

router = APIRouter()

router.include_router(visitor.router, prefix="/visitor", tags=["visitor"])
router.include_router(visitor_auth.router, prefix="/visitor/auth", tags=["visitor-auth"])
router.include_router(auth.router, prefix="/admin/auth", tags=["admin-auth"])
router.include_router(admin.router, prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_access)])
router.include_router(ai.router, prefix="/ai", tags=["ai"])
router.include_router(rag_admin.router, prefix="/admin/rag", tags=["admin-rag"], dependencies=[Depends(require_admin_access)])
router.include_router(analytics.router, prefix="/admin/analytics", tags=["admin-analytics"], dependencies=[Depends(require_admin_access)])
