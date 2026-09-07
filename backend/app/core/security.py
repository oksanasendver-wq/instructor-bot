from app.core.time import utc_now

"""Безопасность и авторизация"""
import hashlib
import hmac
import json
import time
from datetime import timedelta
from typing import Optional
from urllib.parse import parse_qs

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_telegram_init_data(init_data: str) -> dict:
    """
    Проверяет подпись Telegram initData

    Args:
        init_data: строка initData из Telegram WebApp

    Returns:
        dict с данными пользователя

    Raises:
        HTTPException: если подпись неверна или данные устарели
    """
    try:
        # Парсим данные
        parsed = parse_qs(init_data, keep_blank_values=True, strict_parsing=True)
        if any(len(values) != 1 for values in parsed.values()):
            raise ValueError("Duplicate init data fields")
        data_check_string_parts = []

        # Извлекаем hash и auth_date
        received_hash = parsed.get("hash", [None])[0]
        auth_date = parsed.get("auth_date", [None])[0]

        if not received_hash or not auth_date:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing hash or auth_date",
            )

        # Проверяем срок действия (не старше 24 часов)
        auth_timestamp = int(auth_date)
        current_timestamp = int(time.time())
        if auth_timestamp > current_timestamp + 60:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Init data timestamp is in the future",
            )
        if current_timestamp - auth_timestamp > 86400:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Init data is too old"
            )

        # Создаём строку для проверки
        for key, value in sorted(parsed.items()):
            if key != "hash":
                data_check_string_parts.append(f"{key}={value[0]}")

        data_check_string = "\n".join(data_check_string_parts)

        # Вычисляем HMAC
        secret_key = hmac.new(
            b"WebAppData", settings.TELEGRAM_BOT_TOKEN.encode(), hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        # Сравниваем хеши
        if not hmac.compare_digest(calculated_hash, received_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid init data signature",
            )

        # Mini App initData contains a JSON-encoded `user` field. Top-level
        # `id` belongs to a different Telegram login format. Reading it here
        # silently returned 0 even for correctly signed, already linked users.
        # Decode the user only AFTER verifying the signature of the raw data.
        user_data = json.loads(parsed.get("user", ["null"])[0])
        if not isinstance(user_data, dict):
            raise ValueError("Missing Mini App user")
        user_id = user_data.get("id")
        if type(user_id) is not int or not 0 < user_id < 2**52:
            raise ValueError("Invalid Mini App user ID")
        return {**user_data, "auth_date": auth_timestamp}

    except (ValueError, TypeError, UnicodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Mini App user or init data format",
        )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создаёт JWT токен"""
    to_encode = data.copy()

    if expires_delta:
        expire = utc_now() + expires_delta
    else:
        expire = utc_now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_access_token(token: str) -> dict:
    """Проверяет и декодирует JWT токен"""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


def hash_password(password: str) -> str:
    """Хеширует пароль"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет пароль"""
    return pwd_context.verify(plain_password, hashed_password)
