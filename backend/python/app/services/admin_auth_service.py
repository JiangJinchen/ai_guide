import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import AdminSession, AdminUser


PASSWORD_ITERATIONS = 310_000
ACCESS_TOKEN_MINUTES = max(5, int(os.getenv("ADMIN_ACCESS_TOKEN_MINUTES", "15")))
REFRESH_TOKEN_DAYS = max(1, int(os.getenv("ADMIN_REFRESH_TOKEN_DAYS", "7")))
DEVELOPMENT_SECRET = "ai-guide-development-secret-change-before-deployment"


class AuthTokenError(ValueError):
    pass


def hash_password(password: str) -> str:
    if len(password) < 10:
        raise ValueError("管理员密码至少需要 10 个字符")
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


def create_session_tokens(db: Session, user: AdminUser) -> dict:
    now = datetime.now(timezone.utc)
    access_expires = now + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    refresh_expires = now + timedelta(days=REFRESH_TOKEN_DAYS)
    access_token = _encode_token(user, "access", access_expires)
    refresh_token = _encode_token(user, "refresh", refresh_expires)
    db.add(AdminSession(
        admin_user_id=user.id,
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


def token_secret_is_default() -> bool:
    return not bool(os.getenv("ADMIN_TOKEN_SECRET", "").strip())


def _encode_token(user: AdminUser, token_type: str, expires_at: datetime) -> str:
    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
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
    return os.getenv("ADMIN_TOKEN_SECRET", "").strip() or DEVELOPMENT_SECRET


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
