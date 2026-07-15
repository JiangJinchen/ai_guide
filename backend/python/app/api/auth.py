import json
import secrets
import hmac
import re
from datetime import datetime, timezone

import os

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.admin_auth import AVAILABLE_PERMISSIONS, ROLE_LABELS, permissions_for_role, require_admin, require_permission
from app.database import get_db
from app.models import AdminRole, AdminSession, AdminUser, SystemLog
from app.services.admin_auth_service import (
    AuthTokenError,
    REFRESH_TOKEN_DAYS,
    create_session_tokens,
    decode_token,
    hash_refresh_token,
    hash_password,
    verify_password,
)


router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class AdminUserCreate(BaseModel):
    username: str
    password: str
    display_name: str
    role: str


class AdminUserUpdate(BaseModel):
    display_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


class PasswordResetRequest(BaseModel):
    password: str


class AdminRoleCreate(BaseModel):
    role_key: str
    label: str
    permissions: list[str]


class AdminRoleUpdate(BaseModel):
    label: str | None = None
    permissions: list[str] | None = None


def serialize_admin(user: AdminUser, db: Session | None = None) -> dict:
    role = db.query(AdminRole).filter(AdminRole.role_key == user.role).first() if db else None
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "role_label": role.label if role else ROLE_LABELS.get(user.role, user.role),
        "permissions": permissions_for_role(user.role, db),
        "is_active": user.is_active,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
    }


def record_user_action(db: Session, actor: AdminUser, action: str, target: AdminUser, details: dict | None = None):
    db.add(SystemLog(
        level="info",
        source="admin.users",
        message=json.dumps({
            "action": action,
            "resource_type": "admin_user",
            "resource_id": target.id,
            "resource_name": target.username,
            "actor_id": actor.id,
            "actor_name": actor.username,
            "details": details or {},
        }, ensure_ascii=False),
    ))


def record_role_action(db: Session, actor: AdminUser, action: str, target: AdminRole, details: dict | None = None):
    db.add(SystemLog(
        level="info",
        source="admin.roles",
        message=json.dumps({
            "action": action,
            "resource_type": "admin_role",
            "resource_id": target.id,
            "resource_name": target.role_key,
            "actor_id": actor.id,
            "actor_name": actor.username,
            "details": details or {},
        }, ensure_ascii=False),
    ))


def serialize_role(role: AdminRole) -> dict:
    try:
        permissions = json.loads(role.permissions or "[]")
    except (TypeError, json.JSONDecodeError):
        permissions = []
    return {
        "id": role.id,
        "role_key": role.role_key,
        "label": role.label,
        "permissions": permissions if isinstance(permissions, list) else [],
        "is_system": role.is_system,
        "created_at": role.created_at,
        "updated_at": role.updated_at,
    }


def validate_role_permissions(permissions: list[str], allow_all: bool = False) -> list[str]:
    normalized = list(dict.fromkeys(str(value).strip() for value in permissions if str(value).strip()))
    allowed = set(AVAILABLE_PERMISSIONS)
    if allow_all:
        allowed.add("*")
    invalid = [value for value in normalized if value not in allowed]
    if invalid:
        raise HTTPException(status_code=400, detail=f"不支持的权限: {', '.join(invalid)}")
    return normalized


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key="admin_refresh_token",
        value=refresh_token,
        max_age=REFRESH_TOKEN_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=os.getenv("ADMIN_COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes", "on"},
        samesite="lax",
        path="/api/admin/auth",
    )


def set_csrf_cookie(response: Response, token: str | None = None) -> None:
    response.set_cookie(
        key="admin_csrf_token",
        value=token or secrets.token_urlsafe(32),
        max_age=REFRESH_TOKEN_DAYS * 24 * 60 * 60,
        httponly=False,
        secure=os.getenv("ADMIN_COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes", "on"},
        samesite="lax",
        path="/",
    )


def validate_csrf(csrf_cookie: str | None, csrf_header: str | None) -> None:
    if not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=403, detail="CSRF 校验失败，请刷新页面后重试")


@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(AdminUser).filter(AdminUser.username == request.username.strip()).first()
    if not user or not user.is_active or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    user.last_login_at = datetime.now(timezone.utc)
    tokens = create_session_tokens(db, user)
    db.commit()
    response = JSONResponse(jsonable_encoder({
        **tokens,
        "refresh_token": None,
        "user": serialize_admin(user, db),
    }))
    set_refresh_cookie(response, tokens["refresh_token"])
    set_csrf_cookie(response)
    return response


@router.post("/refresh")
async def refresh(
    request: RefreshRequest | None = None,
    refresh_token_cookie: str | None = Cookie(default=None, alias="admin_refresh_token"),
    csrf_cookie: str | None = Cookie(default=None, alias="admin_csrf_token"),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
    db: Session = Depends(get_db),
):
    validate_csrf(csrf_cookie, csrf_header)
    refresh_token = (request.refresh_token if request else None) or refresh_token_cookie
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少刷新令牌")
    try:
        payload = decode_token(refresh_token, "refresh")
    except AuthTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    now = datetime.now(timezone.utc)
    session = db.query(AdminSession).filter(
        AdminSession.refresh_token_hash == hash_refresh_token(refresh_token),
        AdminSession.revoked_at.is_(None),
        AdminSession.expires_at > now,
    ).first()
    user = db.query(AdminUser).filter(
        AdminUser.id == int(payload["sub"]),
        AdminUser.is_active.is_(True),
    ).first()
    if not session or not user or session.admin_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌无效或已撤销")

    session.revoked_at = now
    tokens = create_session_tokens(db, user)
    db.commit()
    response = JSONResponse(jsonable_encoder({
        **tokens,
        "refresh_token": None,
        "user": serialize_admin(user, db),
    }))
    set_refresh_cookie(response, tokens["refresh_token"])
    set_csrf_cookie(response, csrf_cookie)
    return response


@router.post("/logout")
async def logout(
    request: RefreshRequest | None = None,
    refresh_token_cookie: str | None = Cookie(default=None, alias="admin_refresh_token"),
    csrf_cookie: str | None = Cookie(default=None, alias="admin_csrf_token"),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
    db: Session = Depends(get_db),
):
    validate_csrf(csrf_cookie, csrf_header)
    refresh_token = (request.refresh_token if request else None) or refresh_token_cookie
    session = db.query(AdminSession).filter(
        AdminSession.refresh_token_hash == hash_refresh_token(refresh_token),
        AdminSession.revoked_at.is_(None),
    ).first() if refresh_token else None
    if session:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()
    response = JSONResponse({"message": "已退出登录"})
    response.delete_cookie("admin_refresh_token", path="/api/admin/auth")
    response.delete_cookie("admin_csrf_token", path="/")
    return response


@router.get("/me")
async def current_admin(
    user: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return {"user": serialize_admin(user, db)}


@router.get("/users")
async def list_admin_users(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_permission("system.manage")),
):
    users = db.query(AdminUser).order_by(AdminUser.created_at.asc(), AdminUser.id.asc()).all()
    role_rows = db.query(AdminRole).order_by(AdminRole.is_system.desc(), AdminRole.id.asc()).all()
    roles = {role.role_key: role.label for role in role_rows} or ROLE_LABELS
    return {"items": [serialize_admin(user, db) for user in users], "roles": roles}


@router.get("/roles")
async def list_admin_roles(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(require_permission("system.manage")),
):
    roles = db.query(AdminRole).order_by(AdminRole.is_system.desc(), AdminRole.id.asc()).all()
    return {
        "items": [serialize_role(role) for role in roles],
        "permission_options": AVAILABLE_PERMISSIONS,
    }


@router.post("/roles", status_code=201)
async def create_admin_role(
    item: AdminRoleCreate,
    db: Session = Depends(get_db),
    actor: AdminUser = Depends(require_permission("system.manage")),
):
    role_key = item.role_key.strip().lower()
    label = item.label.strip()
    if not re.match(r"^[a-z][a-z0-9_]{2,49}$", role_key):
        raise HTTPException(status_code=400, detail="角色标识需为 3-50 位小写字母、数字或下划线，并以字母开头")
    if not label:
        raise HTTPException(status_code=400, detail="角色名称不能为空")
    if db.query(AdminRole).filter(AdminRole.role_key == role_key).first():
        raise HTTPException(status_code=409, detail="角色标识已存在")
    permissions = validate_role_permissions(item.permissions)
    role = AdminRole(
        role_key=role_key,
        label=label,
        permissions=json.dumps(permissions, ensure_ascii=False),
        is_system=False,
    )
    db.add(role)
    db.flush()
    record_role_action(db, actor, "create", role, {"permissions": permissions})
    db.commit()
    db.refresh(role)
    return {"message": "角色已创建", "role": serialize_role(role)}


@router.put("/roles/{role_id}")
async def update_admin_role(
    role_id: int,
    item: AdminRoleUpdate,
    db: Session = Depends(get_db),
    actor: AdminUser = Depends(require_permission("system.manage")),
):
    role = db.query(AdminRole).filter(AdminRole.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    updates = item.model_dump(exclude_unset=True)
    if "label" in updates:
        updates["label"] = (updates["label"] or "").strip()
        if not updates["label"]:
            raise HTTPException(status_code=400, detail="角色名称不能为空")
        role.label = updates["label"]
    if "permissions" in updates:
        if role.role_key == "admin":
            raise HTTPException(status_code=409, detail="系统管理员权限不可修改")
        permissions = validate_role_permissions(updates["permissions"] or [])
        role.permissions = json.dumps(permissions, ensure_ascii=False)
    record_role_action(db, actor, "update", role, {"fields": sorted(updates.keys())})
    db.commit()
    db.refresh(role)
    return {"message": "角色已更新", "role": serialize_role(role)}


@router.delete("/roles/{role_id}")
async def delete_admin_role(
    role_id: int,
    db: Session = Depends(get_db),
    actor: AdminUser = Depends(require_permission("system.manage")),
):
    role = db.query(AdminRole).filter(AdminRole.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    if role.is_system:
        raise HTTPException(status_code=409, detail="系统角色不能删除")
    if db.query(AdminUser).filter(AdminUser.role == role.role_key).first():
        raise HTTPException(status_code=409, detail="角色仍有管理员账号使用，不能删除")
    record_role_action(db, actor, "delete", role)
    db.delete(role)
    db.commit()
    return {"message": "角色已删除"}


@router.post("/users", status_code=201)
async def create_admin_user(
    item: AdminUserCreate,
    db: Session = Depends(get_db),
    actor: AdminUser = Depends(require_permission("system.manage")),
):
    username = item.username.strip()
    display_name = item.display_name.strip()
    if not username or not display_name:
        raise HTTPException(status_code=400, detail="用户名和显示名称不能为空")
    if not db.query(AdminRole).filter(AdminRole.role_key == item.role).first() and item.role not in ROLE_LABELS:
        raise HTTPException(status_code=400, detail="不支持的管理员角色")
    if db.query(AdminUser).filter(AdminUser.username == username).first():
        raise HTTPException(status_code=409, detail="管理员用户名已存在")
    try:
        user = AdminUser(
            username=username,
            password_hash=hash_password(item.password),
            display_name=display_name,
            role=item.role,
            is_active=True,
        )
        db.add(user)
        db.flush()
        record_user_action(db, actor, "create", user, {"role": user.role})
        db.commit()
        db.refresh(user)
        return {"message": "管理员账号已创建", "user": serialize_admin(user, db)}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建管理员失败: {exc}") from exc


@router.put("/users/{user_id}")
async def update_admin_user(
    user_id: int,
    item: AdminUserUpdate,
    db: Session = Depends(get_db),
    actor: AdminUser = Depends(require_permission("system.manage")),
):
    target = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="管理员账号不存在")
    updates = item.model_dump(exclude_unset=True)
    if "display_name" in updates:
        updates["display_name"] = (updates["display_name"] or "").strip()
        if not updates["display_name"]:
            raise HTTPException(status_code=400, detail="显示名称不能为空")
    if "role" in updates and not db.query(AdminRole).filter(AdminRole.role_key == updates["role"]).first() and updates["role"] not in ROLE_LABELS:
        raise HTTPException(status_code=400, detail="不支持的管理员角色")
    if target.id == actor.id and (updates.get("is_active") is False or updates.get("role", "admin") != "admin"):
        raise HTTPException(status_code=409, detail="不能停用当前账号或移除自己的系统管理员角色")
    for key, value in updates.items():
        setattr(target, key, value)
    if updates.get("is_active") is False:
        db.query(AdminSession).filter(
            AdminSession.admin_user_id == target.id,
            AdminSession.revoked_at.is_(None),
        ).update({AdminSession.revoked_at: datetime.now(timezone.utc)}, synchronize_session=False)
    record_user_action(db, actor, "update", target, {"fields": sorted(updates.keys())})
    db.commit()
    db.refresh(target)
    return {"message": "管理员账号已更新", "user": serialize_admin(target, db)}


@router.put("/users/{user_id}/password")
async def reset_admin_password(
    user_id: int,
    item: PasswordResetRequest,
    db: Session = Depends(get_db),
    actor: AdminUser = Depends(require_permission("system.manage")),
):
    target = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="管理员账号不存在")
    try:
        target.password_hash = hash_password(item.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.query(AdminSession).filter(
        AdminSession.admin_user_id == target.id,
        AdminSession.revoked_at.is_(None),
    ).update({AdminSession.revoked_at: datetime.now(timezone.utc)}, synchronize_session=False)
    record_user_action(db, actor, "reset_password", target)
    db.commit()
    return {"message": "密码已重置，现有会话已撤销"}
