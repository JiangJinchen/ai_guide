import asyncio
import json
import unittest
from http.cookies import SimpleCookie
from types import SimpleNamespace


try:
    from fastapi import HTTPException
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.admin_auth import has_permission
    from app.database import Base
    from app.models import AdminRole, AdminSession, AdminUser, SystemLog
    from app.api.auth import LoginRequest, RefreshRequest, login, logout, refresh
    from app.services.admin_auth_service import hash_password

    AUTH_DEPENDENCIES_AVAILABLE = True
except ModuleNotFoundError:
    AUTH_DEPENDENCIES_AVAILABLE = False


@unittest.skipUnless(AUTH_DEPENDENCIES_AVAILABLE, "fastapi and sqlalchemy are required")
class AdminAuthApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(
            self.engine,
            tables=[AdminRole.__table__, AdminUser.__table__, AdminSession.__table__, SystemLog.__table__],
        )
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db = self.Session()
        self.db.add(AdminRole(
            role_key="admin",
            label="系统管理员",
            permissions='["*"]',
            is_system=True,
        ))
        self.user = AdminUser(
            username="admin",
            password_hash=hash_password("StrongPass123!"),
            display_name="系统管理员",
            role="admin",
            is_active=True,
        )
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_login_serializes_datetimes_and_sets_security_cookies(self):
        response = asyncio.run(login(LoginRequest(username="admin", password="StrongPass123!"), self.db))
        payload = json.loads(response.body)
        cookies = self._cookies(response)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(payload["refresh_token"])
        self.assertIsInstance(payload["user"]["created_at"], str)
        self.assertIsInstance(payload["user"]["last_login_at"], str)
        self.assertTrue(payload["access_token"])
        self.assertTrue(cookies["admin_refresh_token"].value)
        self.assertTrue(cookies["admin_refresh_token"]["httponly"])
        self.assertTrue(cookies["admin_csrf_token"].value)

    def test_refresh_requires_csrf_and_rotates_session(self):
        login_response = asyncio.run(login(LoginRequest(username="admin", password="StrongPass123!"), self.db))
        cookies = self._cookies(login_response)
        refresh_token = cookies["admin_refresh_token"].value
        csrf_token = cookies["admin_csrf_token"].value

        with self.assertRaises(HTTPException) as error:
            asyncio.run(refresh(
                RefreshRequest(),
                refresh_token_cookie=refresh_token,
                csrf_cookie=csrf_token,
                csrf_header="incorrect",
                db=self.db,
            ))
        self.assertEqual(error.exception.status_code, 403)

        response = asyncio.run(refresh(
            RefreshRequest(),
            refresh_token_cookie=refresh_token,
            csrf_cookie=csrf_token,
            csrf_header=csrf_token,
            db=self.db,
        ))
        refreshed_cookies = self._cookies(response)
        self.assertNotEqual(refreshed_cookies["admin_refresh_token"].value, refresh_token)
        self.assertEqual(
            self.db.query(AdminSession).filter(AdminSession.revoked_at.is_not(None)).count(),
            1,
        )

    def test_logout_revokes_session_and_clears_cookies(self):
        login_response = asyncio.run(login(LoginRequest(username="admin", password="StrongPass123!"), self.db))
        cookies = self._cookies(login_response)
        refresh_token = cookies["admin_refresh_token"].value
        csrf_token = cookies["admin_csrf_token"].value

        response = asyncio.run(logout(
            RefreshRequest(),
            refresh_token_cookie=refresh_token,
            csrf_cookie=csrf_token,
            csrf_header=csrf_token,
            db=self.db,
        ))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.db.query(AdminSession).filter(AdminSession.revoked_at.is_not(None)).count(),
            1,
        )
        clear_headers = [
            value.decode("latin-1")
            for key, value in response.raw_headers
            if key.lower() == b"set-cookie"
        ]
        self.assertTrue(any("admin_refresh_token=" in value and "Max-Age=0" in value for value in clear_headers))
        self.assertTrue(any("admin_csrf_token=" in value and "Max-Age=0" in value for value in clear_headers))

    @staticmethod
    def _cookies(response):
        cookies = SimpleCookie()
        for key, value in response.raw_headers:
            if key.lower() == b"set-cookie":
                cookies.load(value.decode("latin-1"))
        return cookies


@unittest.skipUnless(AUTH_DEPENDENCIES_AVAILABLE, "fastapi and sqlalchemy are required")
class RolePermissionTests(unittest.TestCase):
    def test_fixed_roles_are_limited_to_their_domains(self):
        content_user = SimpleNamespace(role="content_operator")
        analyst = SimpleNamespace(role="analyst")
        digital_operator = SimpleNamespace(role="digital_operator")
        admin = SimpleNamespace(role="admin")

        self.assertTrue(has_permission(content_user, "content.write"))
        self.assertFalse(has_permission(content_user, "digital_human.write"))
        self.assertTrue(has_permission(analyst, "analytics.read"))
        self.assertFalse(has_permission(analyst, "content.read"))
        self.assertTrue(has_permission(digital_operator, "digital_human.write"))
        self.assertFalse(has_permission(digital_operator, "system.manage"))
        self.assertTrue(has_permission(admin, "system.manage"))


if __name__ == "__main__":
    unittest.main()
