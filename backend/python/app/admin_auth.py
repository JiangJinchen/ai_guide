import json

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AdminRole, AdminUser
from app.services.admin_auth_service import AuthTokenError, decode_token


bearer_scheme = HTTPBearer(auto_error=False)

ROLE_PERMISSIONS = {
    "admin": {"*"},
    "content_operator": {"content.read", "content.write"},
    "analyst": {"analytics.read"},
    "digital_operator": {"digital_human.read", "digital_human.write"},
}

ROLE_LABELS = {
    "admin": "系统管理员",
    "content_operator": "内容运营",
    "analyst": "数据分析",
    "digital_operator": "数字人运营",
}

AVAILABLE_PERMISSIONS = {
    "content.read": "查看内容",
    "content.write": "维护内容",
    "analytics.read": "查看运营分析",
    "digital_human.read": "查看数字人配置",
    "digital_human.write": "维护数字人配置",
    "system.logs": "查看系统日志",
    "system.manage": "管理账号和角色",
}


def require_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AdminUser:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise _unauthorized("缺少管理员访问令牌")
    try:
        payload = decode_token(credentials.credentials, "access")
    except AuthTokenError as exc:
        raise _unauthorized(str(exc)) from exc

    user = db.query(AdminUser).filter(
        AdminUser.id == int(payload["sub"]),
        AdminUser.is_active.is_(True),
    ).first()
    if not user:
        raise _unauthorized("管理员账号不存在或已停用")
    request.state.admin_user = user
    db.info["admin_user_id"] = user.id
    db.info["admin_username"] = user.username
    db.info["admin_permissions"] = permissions_for_role(user.role, db)
    return user


def require_admin_access(
    request: Request,
    user: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUser:
    permission = _permission_for_request(request)
    if not has_permission(user, permission, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前角色无权执行此操作")
    return user


def require_permission(permission: str):
    def dependency(
        user: AdminUser = Depends(require_admin),
        db: Session = Depends(get_db),
    ) -> AdminUser:
        if not has_permission(user, permission, db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前角色无权执行此操作")
        return user
    return dependency


def permissions_for_role(role: str, db: Session | None = None) -> list[str]:
    if db is not None:
        row = db.query(AdminRole).filter(AdminRole.role_key == role).first()
        if row:
            try:
                values = json.loads(row.permissions or "[]")
                if isinstance(values, list):
                    return [str(value) for value in values]
            except (TypeError, json.JSONDecodeError):
                return []
    permissions = ROLE_PERMISSIONS.get(role, set())
    return ["*"] if "*" in permissions else sorted(permissions)


def has_permission(user: AdminUser, permission: str, db: Session | None = None) -> bool:
    permissions = set(permissions_for_role(user.role, db))
    return "*" in permissions or permission in permissions


def _permission_for_request(request: Request) -> str:
    path = request.url.path
    is_read = request.method.upper() == "GET"
    if path.startswith("/api/admin/analytics") or path.startswith("/api/admin/report"):
        return "analytics.read"
    if path.startswith("/api/admin/logs"):
        return "system.logs"
    if path.startswith("/api/admin/digital-human"):
        return "digital_human.read" if is_read else "digital_human.write"
    content_prefixes = (
        "/api/admin/knowledge",
        "/api/admin/faqs",
        "/api/admin/spots",
        "/api/admin/tickets",
        "/api/admin/activities",
        "/api/admin/spot-guide-assets",
        "/api/admin/rag",
    )
    if path.startswith(content_prefixes):
        return "content.read" if is_read else "content.write"
    return "system.manage"


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
