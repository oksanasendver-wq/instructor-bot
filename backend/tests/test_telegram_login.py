"""Regression tests using signed Mini App data and an isolated local database.

Run: python -m pytest tests/test_telegram_login.py
No Telegram requests or connections to the deployed database are made.
"""

import hashlib
import hmac
import json
import time
from datetime import date, time as clock_time
from urllib.parse import urlencode

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


BOT_TOKEN = "123456789:local-test-bot-token"
WEBHOOK_SECRET = "local-test-webhook-secret"
TELEGRAM_ID = 5_123_456_789


def signed_init_data(**overrides):
    # Mini Apps send user as JSON inside the query string, not top-level id.
    fields = {
        "auth_date": str(int(time.time())),
        "query_id": "local-test-query",
        "user": json.dumps(
            {"id": TELEGRAM_ID, "first_name": "Тест & + ученик"}, ensure_ascii=False
        ),
    }
    fields.update(overrides)
    fields = {key: value for key, value in fields.items() if value is not None}
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(fields.items())
    )
    secret_key = hmac.digest(b"WebAppData", BOT_TOKEN.encode(), "sha256")
    fields["hash"] = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    return urlencode(fields)


@pytest.fixture
def test_settings(monkeypatch):
    # Before importing the app, prevent use of any local production credentials.
    values = {
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "SECRET_KEY": "local-test-secret-key-at-least-32-characters",
        "TELEGRAM_BOT_TOKEN": BOT_TOKEN,
        "TELEGRAM_WEBHOOK_SECRET": WEBHOOK_SECRET,
        "FRONTEND_MINI_APP_URL": "https://miniapp.example.test",
        "FRONTEND_ADMIN_URL": "https://admin.example.test",
        "ENABLE_DEBUG": False,
    }
    for key, value in values.items():
        monkeypatch.setenv(key, str(value))
    from app.core.config import settings

    for key, value in values.items():
        monkeypatch.setattr(settings, key, value)
    return settings


@pytest_asyncio.fixture
async def local_api(test_settings):
    from app.core.database import Base, get_db
    from app.main import app

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def local_db():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = local_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client, sessions
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()


def test_reads_verified_nested_user(test_settings):
    from app.core.security import verify_telegram_init_data

    user = verify_telegram_init_data(signed_init_data())
    assert user["id"] == TELEGRAM_ID
    assert user["first_name"] == "Тест & + ученик"


@pytest.mark.parametrize(
    "user",
    [
        None,
        "null",
        "[]",
        "not-json",
        "{}",
        '{"id":0}',
        '{"id":-1}',
        '{"id":true}',
        '{"id":"123"}',
        '{"id":1.5}',
    ],
)
def test_invalid_or_missing_user_is_rejected(test_settings, user):
    from app.core.security import verify_telegram_init_data
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as error:
        verify_telegram_init_data(signed_init_data(user=user))
    assert error.value.status_code == 401


@pytest.mark.parametrize("offset", [-86401, 300])
def test_expired_or_future_data_is_rejected(test_settings, offset):
    from app.core.security import verify_telegram_init_data
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as error:
        verify_telegram_init_data(
            signed_init_data(auth_date=str(int(time.time()) + offset))
        )
    assert error.value.status_code == 401


def test_tampered_or_ambiguous_data_is_rejected(test_settings):
    from app.core.security import verify_telegram_init_data
    from fastapi import HTTPException

    valid = signed_init_data()
    for invalid in [
        valid.replace(str(TELEGRAM_ID), "111111111"),
        valid + "&auth_date=1",
    ]:
        with pytest.raises(HTTPException) as error:
            verify_telegram_init_data(invalid)
        assert error.value.status_code == 401


def test_all_fields_are_signed_but_identity_comes_only_from_user(test_settings):
    from app.core.security import verify_telegram_init_data
    from fastapi import HTTPException

    signed = signed_init_data(
        id="999", signature="example-ed25519-signature", start_param=""
    )
    assert verify_telegram_init_data(signed)["id"] == TELEGRAM_ID
    with pytest.raises(HTTPException) as error:
        verify_telegram_init_data(
            signed.replace("example-ed25519-signature", "tampered")
        )
    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_linked_instructor_can_log_in_and_read_own_booking(
    local_api, monkeypatch
):
    from datetime import datetime

    frozen = datetime.combine(date.today(), clock_time(10, 30))
    for module in [
        "app.core.time",
        "app.api.instructor.bookings",
        "app.services.lifecycle",
        "app.services.access_control",
    ]:
        monkeypatch.setattr(module + ".school_now", lambda: frozen)
    from app.models import Booking, Client, Instructor

    client, sessions = local_api
    async with sessions() as session:
        instructor = Instructor(
            full_name="Linked instructor",
            phone="7000000001",
            telegram_user_id=TELEGRAM_ID,
        )
        other = Instructor(full_name="Other instructor", phone="7000000002")
        pupil = Client(full_name="Real booking pupil", phone="7000000003")
        session.add_all([instructor, other, pupil])
        await session.flush()
        for owner in [instructor, other]:
            session.add(
                Booking(
                    client_id=pupil.id,
                    instructor_id=owner.id,
                    date=date.today(),
                    start_at=clock_time(10),
                    end_at=clock_time(11),
                    duration_minutes=60,
                    context="Учебная площадка",
                    transmission="МКПП",
                    payment_type="наличные",
                    amount_due=100,
                )
            )
        await session.commit()
        instructor_id = instructor.id

    response = await client.post(
        "/api/instructor/auth/telegram", json={"init_data": signed_init_data()}
    )
    assert response.status_code == 200, response.text
    assert response.json()["instructor"]["id"] == instructor_id
    headers = {"Authorization": "Bearer " + response.json()["access_token"]}
    bookings = await client.get("/api/instructor/bookings/me/today", headers=headers)
    assert bookings.status_code == 200, bookings.text
    assert len(bookings.json()) == 1
    assert bookings.json()[0]["client"]["full_name"] == "Real booking pupil"


@pytest.mark.asyncio
@pytest.mark.parametrize("phone", ["7000000001", "+7 700 000 00 01", "87000000001"])
async def test_contact_is_saved_and_next_login_succeeds(local_api, phone):
    from app.models import Instructor

    client, sessions = local_api
    async with sessions() as session:
        session.add(Instructor(full_name="Unlinked instructor", phone=phone))
        await session.commit()
    initial = await client.post(
        "/api/instructor/auth/telegram", json={"init_data": signed_init_data()}
    )
    assert initial.status_code == 403
    webhook = await client.post(
        "/api/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": WEBHOOK_SECRET},
        json={
            "update_id": 1,
            "message": {
                "from": {"id": TELEGRAM_ID},
                "chat": {"id": TELEGRAM_ID, "type": "private"},
                "contact": {
                    "user_id": TELEGRAM_ID,
                    "phone_number": "+77000000001",
                    "first_name": "Test",
                },
            },
        },
    )
    assert webhook.status_code == 200, webhook.text
    async with sessions() as session:
        instructor = (await session.execute(select(Instructor))).scalar_one()
        assert instructor.telegram_user_id == TELEGRAM_ID
    login = await client.post(
        "/api/instructor/auth/telegram", json={"init_data": signed_init_data()}
    )
    assert login.status_code == 200, login.text


@pytest.mark.asyncio
async def test_inactive_instructor_cannot_log_in(local_api):
    from app.models import Instructor

    client, sessions = local_api
    async with sessions() as session:
        session.add(
            Instructor(
                full_name="Inactive",
                phone="7000000001",
                telegram_user_id=TELEGRAM_ID,
                is_active=False,
            )
        )
        await session.commit()
    result = await client.post(
        "/api/instructor/auth/telegram", json={"init_data": signed_init_data()}
    )
    assert result.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("secret", [None, "wrong-secret"])
async def test_webhook_rejects_missing_or_wrong_secret(local_api, secret):
    client, _ = local_api
    headers = {"X-Telegram-Bot-Api-Secret-Token": secret} if secret else {}
    response = await client.post(
        "/api/telegram/webhook", headers=headers, json={"update_id": 1}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("owner_id", [None, TELEGRAM_ID + 1])
async def test_unverified_contact_cannot_link_an_instructor(local_api, owner_id):
    from app.models import Instructor

    client, sessions = local_api
    async with sessions() as session:
        session.add(Instructor(full_name="Unlinked", phone="7000000001"))
        await session.commit()
    contact = {"phone_number": "+77000000001", "first_name": "Test"}
    if owner_id is not None:
        contact["user_id"] = owner_id
    result = await client.post(
        "/api/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": WEBHOOK_SECRET},
        json={
            "update_id": 1,
            "message": {
                "from": {"id": TELEGRAM_ID},
                "chat": {"id": TELEGRAM_ID, "type": "private"},
                "contact": contact,
            },
        },
    )
    assert result.status_code == 200
    async with sessions() as session:
        assert (
            await session.execute(select(Instructor))
        ).scalar_one().telegram_user_id is None
