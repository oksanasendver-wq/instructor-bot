"""Авторизация администратора"""

import hmac
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import create_access_token

router = APIRouter()


class AdminLoginRequest(BaseModel):
    """Логин администратора"""

    username: str
    password: str


class AdminAuthResponse(BaseModel):
    """Ответ с токеном"""

    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=AdminAuthResponse)
async def admin_login(request: AdminLoginRequest):
    """Authenticate the school administrator configured through environment secrets."""
    if not hmac.compare_digest(
        request.username.encode(), settings.ADMIN_USERNAME.encode()
    ) or not hmac.compare_digest(
        request.password.encode(), settings.ADMIN_PASSWORD.encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    # Создаём токен
    token = create_access_token(data={"sub": "admin", "type": "admin"})

    return AdminAuthResponse(access_token=token)
