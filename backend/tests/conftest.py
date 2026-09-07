"""All tests use an isolated database; production .env is never used."""

import os

for key, value in {
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "SECRET_KEY": "isolated-test-secret-at-least-32-characters",
    "TELEGRAM_BOT_TOKEN": "123456789:local-test-bot-token",
    "TELEGRAM_WEBHOOK_SECRET": "local-test-webhook-secret",
    "ADMIN_USERNAME": "test-admin",
    "ADMIN_PASSWORD": "test-password",
    "FRONTEND_MINI_APP_URL": "http://localhost:5173",
    "FRONTEND_ADMIN_URL": "http://localhost:5174",
    "GROQ_API_KEY": "",
    "NVIDIA_API_KEY": "",
    "TIMEZONE": "Asia/Almaty",
    "ENABLE_DEBUG": "false",
}.items():
    os.environ[key] = value

from datetime import datetime
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models import Instructor, Client
from scripts.seed_data import seed_all


@pytest_asyncio.fixture
async def school(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def db_override():
        async with sessions() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = db_override
    clock = {"now": datetime(2026, 9, 6, 12, 0)}
    import app.core.time as time_module
    import app.api.instructor.bookings as ib
    import app.api.admin.bookings as ab
    import app.services.lifecycle as lifecycle
    import app.services.access_control as access

    for module in (time_module, ib, ab, lifecycle, access):
        monkeypatch.setattr(module, "school_now", lambda: clock["now"])
    async with sessions() as session:
        await seed_all(session)
        session.add_all(
            [
                Instructor(
                    id=1,
                    full_name="Алексей Иванов",
                    phone="+77001234567",
                    telegram_user_id=5123456789,
                    transmission="АКПП",
                ),
                Instructor(
                    id=2,
                    full_name="Второй Инструктор",
                    phone="+77001234568",
                    telegram_user_id=5123456790,
                ),
                Client(id=1, full_name="Мария Сидорова", phone="+77001234569"),
                Client(id=2, full_name="Иван Петров", phone="+77001234570"),
            ]
        )
        await session.commit()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http:
        yield {
            "http": http,
            "sessions": sessions,
            "clock": clock,
            "admin": {
                "Authorization": "Bearer "
                + create_access_token({"sub": "admin", "type": "admin"})
            },
            "instructor": {
                "Authorization": "Bearer "
                + create_access_token({"sub": "1", "type": "instructor"})
            },
            "other": {
                "Authorization": "Bearer "
                + create_access_token({"sub": "2", "type": "instructor"})
            },
        }
    app.dependency_overrides.clear()
    await engine.dispose()
