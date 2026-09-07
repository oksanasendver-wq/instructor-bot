"""Webhook Telegram: связывает инструктора с его аккаунтом после requestContact."""

import re
import logging
import hmac

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models import Instructor

router = APIRouter()
logger = logging.getLogger("uvicorn.error")


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    # Казахстанский номер в админке часто вводят без кода страны (10 цифр),
    # а Telegram отправляет его как +7XXXXXXXXXX. Сравниваем один формат.
    if len(digits) == 10:
        return f"7{digits}"
    if len(digits) == 11 and digits.startswith("8"):
        return f"7{digits[1:]}"
    return digits


async def send_start_message(chat_id: int) -> None:
    """Give /start a usable Mini App button; the frontend remains hosted on Vercel."""
    payload = {
        "chat_id": chat_id,
        "text": "Откройте приложение инструктора кнопкой ниже.",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {
                        "text": "Открыть приложение",
                        "web_app": {"url": settings.FRONTEND_MINI_APP_URL},
                    }
                ]
            ],
        },
    }
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json=payload,
        )


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Accept only Telegram updates and bind a contact shared from the Mini App."""
    if not settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=503, detail="Подтверждение контакта не настроено"
        )
    if not hmac.compare_digest(
        x_telegram_bot_api_secret_token or "", settings.TELEGRAM_WEBHOOK_SECRET
    ):
        raise HTTPException(status_code=403, detail="Invalid Telegram webhook secret")

    payload = await request.json()
    message = payload.get("message") or payload.get("edited_message") or {}
    if message.get("text", "").startswith("/start") and message.get("chat", {}).get(
        "id"
    ):
        await send_start_message(message["chat"]["id"])
        return {"ok": True}

    contact = message.get("contact") or {}
    if not contact:
        return {"ok": True}
    # message.from is the Telegram account that actually sent the contact.
    # It is more reliable than a stale/forwarded contact payload for linking.
    telegram_user_id = (message.get("from") or {}).get("id")
    phone = normalize_phone(contact.get("phone_number", ""))
    # A manually shared contact need not have an owner ID. The sender alone
    # does not prove ownership of its phone: require the sender's own contact.
    contact_owner_id = contact.get("user_id")
    if (
        not telegram_user_id
        or not phone
        or contact_owner_id != telegram_user_id
        or (message.get("chat", {}).get("type") != "private")
    ):
        logger.info(
            "telegram_contact outcome=unverified_contact telegram_user_id=%s",
            telegram_user_id,
        )
        return {"ok": True}

    instructors = (
        (await db.execute(select(Instructor).where(Instructor.is_active.is_(True))))
        .scalars()
        .all()
    )
    instructor = next(
        (item for item in instructors if normalize_phone(item.phone) == phone), None
    )
    if not instructor:
        logger.info(
            "telegram_contact outcome=no_active_phone_match telegram_user_id=%s",
            telegram_user_id,
        )
        return {"ok": True}
    # A repeated confirmed contact is an intentional recovery path if an
    # administrator previously linked the instructor to the wrong account.
    instructor.telegram_user_id = telegram_user_id
    await db.commit()
    logger.info(
        "telegram_contact outcome=linked instructor_id=%s telegram_user_id=%s",
        instructor.id,
        telegram_user_id,
    )
    return {"ok": True}
