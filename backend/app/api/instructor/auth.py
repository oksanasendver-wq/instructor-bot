"""Авторизация инструктора через Telegram"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import verify_telegram_init_data, create_access_token
from app.models import Instructor

router = APIRouter()
logger = logging.getLogger("uvicorn.error")


class TelegramAuthRequest(BaseModel):
    """Telegram initData"""

    init_data: str


class AuthResponse(BaseModel):
    """Ответ с токеном"""

    access_token: str
    token_type: str = "bearer"
    instructor: dict


@router.post("/telegram", response_model=AuthResponse)
async def telegram_auth(
    request: TelegramAuthRequest, db: AsyncSession = Depends(get_db)
):
    """
    Первичная проверка Telegram initData

    Проверяет подпись и возвращает telegram_user_id.
    Если инструктор уже привязан — возвращает токен сразу.
    Если нет — требует подтверждение номера телефона.
    """
    # Проверяем initData
    user_data = verify_telegram_init_data(request.init_data)
    telegram_user_id = user_data["id"]

    # Ищем инструктора по telegram_user_id
    query = select(Instructor).where(
        Instructor.telegram_user_id == telegram_user_id, Instructor.is_active == True
    )
    result = await db.execute(query)
    instructor = result.scalars().first()

    if instructor:
        logger.info("telegram_auth outcome=authorized instructor_id=%s", instructor.id)
        # Уже привязан — выдаём токен
        token = create_access_token(
            data={
                "sub": str(instructor.id),
                "type": "instructor",
                "telegram_user_id": telegram_user_id,
            }
        )

        return AuthResponse(
            access_token=token,
            instructor={
                "id": instructor.id,
                "full_name": instructor.full_name,
                "phone": instructor.phone,
                "transmission": instructor.transmission,
            },
        )

    # Не привязан — требуем подтверждение номера
    logger.info(
        "telegram_auth outcome=not_linked telegram_user_id=%s", telegram_user_id
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Phone confirmation required"
    )
