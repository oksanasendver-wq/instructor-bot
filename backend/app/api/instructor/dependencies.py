"""Dependencies для API инструктора"""

from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_access_token
from app.models import Instructor


async def get_current_instructor(
    authorization: str | None = Header(None), db: AsyncSession = Depends(get_db)
) -> Instructor:
    """
    Dependency для получения текущего инструктора из JWT токена

    Проверяет токен и возвращает объект Instructor
    """
    # Проверяем формат
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    token = authorization.replace("Bearer ", "")

    # Декодируем токен
    payload = verify_access_token(token)

    # Проверяем тип
    if payload.get("type") != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token type"
        )

    try:
        instructor_id = int(payload.get("sub", ""))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=401, detail="Сессия недействительна. Войдите снова"
        )

    # Получаем инструктора
    query = select(Instructor).where(
        Instructor.id == instructor_id, Instructor.is_active == True
    )
    result = await db.execute(query)
    instructor = result.scalars().first()

    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instructor not found or not active",
        )

    return instructor
