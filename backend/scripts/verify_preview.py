"""Run only against scripts/local_preview.py and local Vite previews."""

import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright, expect

ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts"


async def main():
    errors = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 390, "height": 844})
        page = await ctx.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto("http://127.0.0.1:5173")
        await expect(page.get_by_role("heading", name="Мария Сидорова")).to_be_visible()
        await page.screenshot(path=str(ARTIFACTS / "miniapp-today.png"))
        await page.set_viewport_size({"width": 320, "height": 720})
        assert await page.evaluate(
            "document.documentElement.scrollWidth <= innerWidth"
        ), "Mobile overflow"
        await page.screenshot(path=str(ARTIFACTS / "miniapp-320.png"))
        await page.evaluate("document.documentElement.dataset.theme='dark'")
        await page.screenshot(path=str(ARTIFACTS / "miniapp-dark.png"))
        await page.evaluate("document.documentElement.dataset.theme='light'")
        await page.set_viewport_size({"width": 390, "height": 844})
        if await page.get_by_role("button", name="Пришёл", exact=True).count():
            await page.get_by_role("button", name="Пришёл", exact=True).click()
        await expect(page.get_by_text("Идёт занятие", exact=True)).to_be_visible()
        if await page.get_by_role(
            "button", name=re.compile("Подтвердить получение")
        ).count():
            await page.get_by_role(
                "button", name=re.compile("Подтвердить получение")
            ).click()
        await expect(page.get_by_text("Получено", exact=True)).to_be_visible()
        print("ATTENDANCE + PAYMENT OK", flush=True)
        await page.request.post("http://127.0.0.1:8010/__preview/clock?minutes=61")
        await page.reload()
        await page.get_by_role("button", name="Завершить", exact=True).click()
        await expect(
            page.get_by_role("heading", name="Как прошло занятие?")
        ).to_be_visible()
        await page.locator(".chips").first.get_by_role("button").first.click()
        for button in await page.get_by_role("button", name=re.compile(": 3$")).all():
            await button.click()
        await page.get_by_role("button", name="A3 Самостоятельно").click()
        await page.get_by_role("button", name="Общая оценка 4", exact=True).click()
        await page.locator("textarea").last.fill(
            "Проверка интерфейса: увереннее работает с зеркалами."
        )
        await page.screenshot(
            path=str(ARTIFACTS / "miniapp-report.png"), full_page=True
        )
        await page.get_by_role("button", name="Сохранить отчёт", exact=True).click()
        await expect(page.get_by_role("heading", name="Отчёт сохранён")).to_be_visible()
        await page.screenshot(path=str(ARTIFACTS / "miniapp-success.png"))
        await page.get_by_role("link", name="К карточке ученика").click()
        await expect(page.get_by_role("heading", name="Мария Сидорова")).to_be_visible()
        await page.screenshot(
            path=str(ARTIFACTS / "miniapp-profile.png"), full_page=True
        )
        print("REPORT + PROFILE OK", flush=True)
        admin = await browser.new_page(viewport={"width": 1440, "height": 1000})
        admin.on("pageerror", lambda error: errors.append(str(error)))
        await admin.goto("http://127.0.0.1:5174")
        await admin.get_by_label("Логин").fill("local-admin")
        await admin.get_by_label("Пароль", exact=True).fill("instructor-local")
        await admin.get_by_role("button", name=re.compile("Войти")).click()
        await expect(
            admin.get_by_role("heading", name="Школа в движении")
        ).to_be_visible()
        await admin.screenshot(path=str(ARTIFACTS / "admin-dashboard.png"))
        await admin.get_by_role("link", name="Ученики", exact=True).click()
        await admin.get_by_role("button", name="Добавить ученика", exact=True).click()
        await admin.get_by_label("Имя и фамилия *").fill("Тестовый Ученик")
        await admin.get_by_label("Телефон *").fill("+77007778899")
        await admin.get_by_role("button", name="Сохранить карточку").click()
        row = admin.get_by_role("row").filter(has_text="Тестовый Ученик")
        await expect(row).to_be_visible()
        await row.get_by_role("button", name="Изменить Тестовый Ученик").click()
        await admin.get_by_label("Имя и фамилия *").fill("Проверенный Ученик")
        await admin.get_by_role("button", name="Сохранить карточку").click()
        await admin.get_by_role("button", name="Удалить Проверенный Ученик").click()
        await (
            admin.get_by_role("dialog")
            .get_by_role("button", name="Удалить", exact=True)
            .click()
        )
        await expect(admin.get_by_text("Проверенный Ученик", exact=True)).to_have_count(
            0
        )
        await admin.goto("http://127.0.0.1:5174/#/clients/2")
        await expect(
            admin.get_by_role("heading", name="Прогресс ученика", level=1)
        ).to_be_visible()
        await expect(admin.get_by_role("img", name="85 из 100")).to_be_visible()
        await admin.screenshot(
            path=str(ARTIFACTS / "admin-profile.png"), full_page=True
        )
        await admin.get_by_role("button", name="Для бумажной книжки").click()
        await expect(admin.get_by_role("dialog")).to_be_visible()
        await admin.pdf(path=str(ARTIFACTS / "practice-booklet.pdf"), format="A4")
        await admin.get_by_role("button", name="Закрыть", exact=True).click()
        await admin.get_by_role("link", name="Инструкторы", exact=True).click()
        await admin.get_by_role("button", name="Добавить инструктора").click()
        await admin.get_by_label("Имя и фамилия *").fill("Проверка Инструктор")
        await admin.get_by_label("Телефон *").fill("+77009990088")
        await admin.get_by_role("button", name="Сохранить карточку").click()
        await admin.get_by_role("button", name="Изменить Проверка Инструктор").click()
        await admin.get_by_label("Коробка передач").select_option("АКПП")
        await admin.get_by_role("button", name="Сохранить карточку").click()
        await admin.get_by_role(
            "button", name="Архивировать Проверка Инструктор"
        ).click()
        await (
            admin.get_by_role("dialog")
            .get_by_role("button", name="В архив", exact=True)
            .click()
        )
        await expect(
            admin.get_by_role("row")
            .filter(has_text="Проверка Инструктор")
            .get_by_text("Архив", exact=True)
        ).to_be_visible()
        print("ADMIN CRUD + PROFILE + PRINT OK", flush=True)
        assert not errors, errors
        await browser.close()
    print("LOCAL BROWSER WORKFLOW PASSED", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
