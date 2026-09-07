"""Dependencies для Admin API"""

from fastapi import HTTPException, status, Header

from app.core.security import verify_access_token


async def get_current_admin(authorization: str | None = Header(None)) -> dict:
    """
    Dependency для проверки администратора

    Проверяет JWT токен и тип 'admin'
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    token = authorization.replace("Bearer ", "")
    payload = verify_access_token(token)

    if payload.get("type") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    return payload
