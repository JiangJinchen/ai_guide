import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AppUser, AppUserSession

PASSWORD_ITERATIONS = 310_000
ACCESS_TOKEN_MINUTES = max(5, int(os.getenv("VISITOR_ACCESS_TOKEN_MINUTES", "60")))
REFRESH_TOKEN_DAYS = max(1, int(os.getenv("VISITOR_REFRESH_TOKEN_DAYS", "30")))
DEVELOPMENT_SECRET = "ai-guide-visitor-development-secret-change-before-deployment"


class AuthTokenError(ValueError):
    pass


def hash_password(password: str) -> str:
    if len(password) < 6:
        raise ValueError("密码至少需要 6 个字符")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = _b64decode(salt_text)
        expected = _b64decode(digest_text)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False


def create_session_tokens(db: Session, user: AppUser) -> dict:
    now = datetime.now(timezone.utc)
    access_expires = now + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    refresh_expires = now + timedelta(days=REFRESH_TOKEN_DAYS)
    access_token = _encode_token(user, "access", access_expires)
    refresh_token = _encode_token(user, "refresh", refresh_expires)
    db.add(AppUserSession(
        app_user_id=user.id,
        refresh_token_hash=hash_refresh_token(refresh_token),
        expires_at=refresh_expires,
    ))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_MINUTES * 60,
    }


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload_text, signature_text = token.split(".", 1)
        expected_signature = hmac.new(
            _token_secret().encode("utf-8"), payload_text.encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(expected_signature, _b64decode(signature_text)):
            raise AuthTokenError("令牌签名无效")
        payload = json.loads(_b64decode(payload_text).decode("utf-8"))
    except AuthTokenError:
        raise
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AuthTokenError("令牌格式无效") from exc

    if payload.get("type") != expected_type:
        raise AuthTokenError("令牌类型无效")
    if int(payload.get("exp", 0)) <= int(time.time()):
        raise AuthTokenError("令牌已过期")
    return payload


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _encode_token(user: AppUser, token_type: str, expires_at: datetime) -> str:
    payload = {
        "sub": user.id,
        "phone": user.phone,
        "type": token_type,
        "iat": int(time.time()),
        "exp": int(expires_at.timestamp()),
        "jti": secrets.token_urlsafe(12),
    }
    payload_text = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(
        _token_secret().encode("utf-8"), payload_text.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{payload_text}.{_b64encode(signature)}"


def _token_secret() -> str:
    return os.getenv("VISITOR_TOKEN_SECRET", "").strip() or DEVELOPMENT_SECRET


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def require_visitor(db: Session = Depends(get_db)):
    from fastapi import Header
    auth_header = Header(default=None, alias="Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权访问")
    token = auth_header[7:]
    try:
        payload = decode_token(token, "access")
    except AuthTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    user = db.query(AppUser).filter(AppUser.id == int(payload["sub"]), AppUser.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在或已被禁用")
    return user


router = APIRouter()


class RegisterRequest(BaseModel):
    phone: str
    password: str
    nickname: str = "游客"


class LoginRequest(BaseModel):
    phone: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    phone: str
    nickname: str
    avatar_url: str | None
    created_at: datetime


def serialize_user(user: AppUser) -> dict:
    return {
        "id": user.id,
        "phone": user.phone,
        "nickname": user.nickname or "游客",
        "avatar_url": user.avatar_url,
        "created_at": user.created_at,
    }


@router.post("/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    phone = request.phone.strip()
    password = request.password.strip()
    nickname = request.nickname.strip() or "游客"

    if not phone:
        raise HTTPException(status_code=400, detail="手机号不能为空")
    if not password:
        raise HTTPException(status_code=400, detail="密码不能为空")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码至少需要6个字符")

    if db.query(AppUser).filter(AppUser.phone == phone).first():
        raise HTTPException(status_code=409, detail="该手机号已注册")

    try:
        user = AppUser(
            phone=phone,
            password_hash=hash_password(password),
            nickname=nickname,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        tokens = create_session_tokens(db, user)
        db.commit()
        return JSONResponse(jsonable_encoder({
            **tokens,
            "user": serialize_user(user),
        }))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"注册失败: {exc}") from exc


@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    phone = request.phone.strip()
    password = request.password.strip()

    if not phone or not password:
        raise HTTPException(status_code=400, detail="手机号和密码不能为空")

    user = db.query(AppUser).filter(AppUser.phone == phone).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="手机号或密码错误")

    if not user.password_hash or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="手机号或密码错误")

    user.last_login_at = datetime.now(timezone.utc)
    tokens = create_session_tokens(db, user)
    db.commit()

    return JSONResponse(jsonable_encoder({
        **tokens,
        "user": serialize_user(user),
    }))


@router.post("/refresh")
async def refresh(request: RefreshRequest, db: Session = Depends(get_db)):
    refresh_token = request.refresh_token
    if not refresh_token:
        raise HTTPException(status_code=401, detail="缺少刷新令牌")

    try:
        payload = decode_token(refresh_token, "refresh")
    except AuthTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    now = datetime.now(timezone.utc)
    session = db.query(AppUserSession).filter(
        AppUserSession.refresh_token_hash == hash_refresh_token(refresh_token),
        AppUserSession.revoked_at.is_(None),
        AppUserSession.expires_at > now,
    ).first()
    user = db.query(AppUser).filter(
        AppUser.id == int(payload["sub"]),
        AppUser.is_active.is_(True),
    ).first()

    if not session or not user or session.app_user_id != user.id:
        raise HTTPException(status_code=401, detail="刷新令牌无效或已撤销")

    session.revoked_at = now
    tokens = create_session_tokens(db, user)
    db.commit()

    return JSONResponse(jsonable_encoder({
        **tokens,
        "user": serialize_user(user),
    }))


@router.post("/logout")
async def logout(request: RefreshRequest, db: Session = Depends(get_db)):
    refresh_token = request.refresh_token
    if refresh_token:
        session = db.query(AppUserSession).filter(
            AppUserSession.refresh_token_hash == hash_refresh_token(refresh_token),
            AppUserSession.revoked_at.is_(None),
        ).first()
        if session:
            session.revoked_at = datetime.now(timezone.utc)
            db.commit()
    return {"message": "已退出登录"}


@router.get("/me")
async def current_user(user: AppUser = Depends(require_visitor)):
    return {"user": serialize_user(user)}