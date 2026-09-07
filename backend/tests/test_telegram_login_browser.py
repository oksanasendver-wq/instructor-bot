"""Verify the existing production Mini App bundle against the real local API.

Build frontend-miniapp first. Install playwright and its chromium browser to run.
Telegram delivery is simulated; every browser request is intercepted locally.
"""

import json
from pathlib import Path
from urllib.parse import urlencode, urlparse

import pytest

from tests.test_telegram_login import (  # noqa: F401 - shared pytest fixtures
    TELEGRAM_ID,
    WEBHOOK_SECRET,
    local_api,
    signed_init_data,
    test_settings,
)

playwright = pytest.importorskip("playwright.async_api")
DIST = Path(__file__).resolve().parents[2] / "frontend-miniapp" / "dist"


@pytest.mark.asyncio
@pytest.mark.skipif(
    not (DIST / "index.html").exists(), reason="Build frontend-miniapp first"
)
@pytest.mark.parametrize("already_linked", [True, False])
async def test_miniapp_opens_today_after_authentication(
    local_api, already_linked, tmp_path
):
    from app.models import Instructor

    client, sessions = local_api
    async with sessions() as session:
        session.add(
            Instructor(
                full_name="Browser test instructor",
                phone="7000000001",
                telegram_user_id=TELEGRAM_ID if already_linked else None,
            )
        )
        await session.commit()
    init_data = signed_init_data()
    telegram_script = """
        window.TelegramWebviewProxy = {postEvent() {}};
        window.Telegram = { WebApp: {
            initData: INIT_DATA, ready() {}, expand() {},
            requestContact(callback) {
                fetch('/test-deliver-contact', {method: 'POST'})
                    .then(() => callback(true));
            }
        }};
    """.replace("INIT_DATA", json.dumps(init_data))
    auth_statuses = []
    page_errors = []

    async def serve(route):
        request = route.request
        path = urlparse(request.url).path
        if path == "/js/telegram-web-app.js":
            await route.fulfill(content_type="text/javascript", body=telegram_script)
        elif path == "/test-deliver-contact":
            result = await client.post(
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
            assert result.status_code == 200
            await route.fulfill(json={"ok": True})
        elif path.startswith("/api/"):
            if request.method == "OPTIONS":
                await route.fulfill(
                    status=200,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "*",
                        "Access-Control-Allow-Methods": "*",
                    },
                )
                return
            result = await client.request(
                request.method, path, content=request.post_data, headers=request.headers
            )
            if path.endswith("/auth/telegram"):
                auth_statuses.append(result.status_code)
            await route.fulfill(
                status=result.status_code,
                body=result.content,
                content_type="application/json",
                headers={"Access-Control-Allow-Origin": "*"},
            )
        else:
            asset = (DIST / (path.lstrip("/") or "index.html")).resolve()
            if asset.is_relative_to(DIST) and asset.is_file():
                await route.fulfill(path=str(asset))
            else:
                # Never allow a request to the deployed app, Telegram, or other servers.
                await route.fulfill(
                    status=404, body="Local browser test: resource not found"
                )

    async with playwright.async_playwright() as engine:
        browser = await engine.chromium.launch()
        try:
            page = await browser.new_page(viewport={"width": 390, "height": 780})
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            await page.route("**/*", serve)
            launch_params = urlencode(
                {
                    "tgWebAppData": init_data,
                    "tgWebAppVersion": "7.10",
                    "tgWebAppPlatform": "tdesktop",
                    "tgWebAppThemeParams": "{}",
                }
            )
            await page.goto("http://miniapp.local.test/#" + launch_params)
            if not already_linked:
                await playwright.expect(
                    page.get_by_role("heading", name="Давайте знакомиться")
                ).to_be_visible()
                await page.get_by_role(
                    "button", name="Подтвердить номер", exact=True
                ).click()
            await playwright.expect(
                page.get_by_role("navigation", name="Основная навигация", exact=True)
            ).to_be_visible(timeout=15000)
            await playwright.expect(
                page.get_by_text("В расписании свободно", exact=True)
            ).to_be_visible()
            await page.screenshot(path=str(tmp_path / "telegram-today.png"))
            assert auth_statuses[-1] == 200
            assert not page_errors
            await page.reload()
            await playwright.expect(
                page.get_by_role("navigation", name="Основная навигация", exact=True)
            ).to_be_visible()
        finally:
            await browser.close()
