import hmac

from fastapi import Request
from sqladmin.authentication import AuthenticationBackend

from app.auth.password_utils import PasswordUtils
from config import settings


class AdminAuthBackend(AuthenticationBackend):
    def __init__(self, secret_key: str) -> None:
        super().__init__(secret_key=secret_key)
        self.password_utils = PasswordUtils()

    def _verify_credentials(self, username: str, password: str) -> bool:
        if not settings.admin_username:
            return False

        if not hmac.compare_digest(username, settings.admin_username):
            return False

        if settings.admin_password_hash:
            return self.password_utils.verify_password(
                password, settings.admin_password_hash
            )

        if settings.admin_password:
            return hmac.compare_digest(password, settings.admin_password)

        return False

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))

        if not self._verify_credentials(username=username, password=password):
            return False

        request.session.update(
            {
                "admin_authenticated": True,
                "admin_username": username,
            }
        )
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return bool(request.session.get("admin_authenticated"))
