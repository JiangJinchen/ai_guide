"""Create or update the initial administrator from environment variables."""

import os

from dotenv import load_dotenv

from app.database import SessionLocal
from app.models import AdminUser
from app.services.admin_auth_service import hash_password


def seed_admin() -> AdminUser:
    load_dotenv()
    username = os.getenv("ADMIN_BOOTSTRAP_USERNAME", "").strip()
    password = os.getenv("ADMIN_BOOTSTRAP_PASSWORD", "")
    display_name = os.getenv("ADMIN_BOOTSTRAP_DISPLAY_NAME", "系统管理员").strip() or "系统管理员"
    if not username or not password:
        raise RuntimeError("请设置 ADMIN_BOOTSTRAP_USERNAME 和 ADMIN_BOOTSTRAP_PASSWORD")

    db = SessionLocal()
    try:
        user = db.query(AdminUser).filter(AdminUser.username == username).first()
        if user:
            user.password_hash = hash_password(password)
            user.display_name = display_name
            user.role = "admin"
            user.is_active = True
        else:
            user = AdminUser(
                username=username,
                password_hash=hash_password(password),
                display_name=display_name,
                role="admin",
                is_active=True,
            )
            db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    admin = seed_admin()
    print(f"管理员账号已就绪：{admin.username}")
