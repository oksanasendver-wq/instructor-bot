"""Production bundles against an isolated real API/database, never deployed services."""
import json
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

import pytest
from app.core.time import utc_now
from app.models import LessonReport
from tests.integration.test_workflow import new_booking, submit, arrived_and_finished

playwright = pytest.importorskip('playwright.async_api')
DIST = Path(__file__).resolve().parents[2] / 'frontend-miniapp' / 'dist'
pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(not (DIST / 'index.html').exists(), reason='Build miniapp first')]


async def open_app(browser, school, route_path, admin=False):
    bundle = DIST.parent.parent / 'frontend-admin' / 'dist' if admin else DIST
    page = await browser.new_page(viewport={'width': 1280 if admin else 320, 'height': 780})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    actor = 'admin' if admin else 'instructor'
    token = school[actor]['Authorization'].removeprefix('Bearer ')
    await page.add_init_script('localStorage.setItem(' + json.dumps(actor + '_token') + ', ' + json.dumps(token) + ')')

    async def serve(route):
        request = route.request
        parsed = urlparse(request.url)
        if parsed.path == '/js/telegram-web-app.js':
            await route.fulfill(content_type='text/javascript', body='')
        elif parsed.path.startswith(('/api/', '/admin/')):
            result = await school['http'].request(request.method, parsed.path + ('?' + parsed.query if parsed.query else ''), content=request.post_data, headers=request.headers)
            await route.fulfill(status=result.status_code, body=result.content, content_type='application/json', headers={'Access-Control-Allow-Origin': '*'})
        else:
            asset = (bundle / (parsed.path.lstrip('/') or 'index.html')).resolve()
            if asset.is_relative_to(bundle) and asset.is_file():
                await route.fulfill(path=str(asset))
            else:
                await route.fulfill(status=404, body='External requests disabled')

    await page.route('**/*', serve)
    await page.goto('http://miniapp.local.test/#' + route_path)
    return page, errors


async def test_profile_real_data_lesson_read_and_account_navigation(school, tmp_path):
    booking = await new_booking(school, context='Учебная площадка')
    saved = await submit(school, booking)
    async with school['sessions']() as db:
        report = await db.get(LessonReport, saved['report_id'])
        report.edited_until = utc_now() - timedelta(days=1)
        await db.commit()
    async with playwright.async_playwright() as engine:
        browser = await engine.chromium.launch()
        try:
            page, errors = await open_app(browser, school, '/client/1')
            await playwright.expect(page.get_by_role('heading', name='Оценка вождения', exact=True)).to_be_visible()
            city = page.locator('.score-tile').filter(has=page.get_by_text('Город', exact=True))
            await playwright.expect(city.locator('strong')).to_have_text('—')
            await playwright.expect(page.get_by_text('Пока одна оценка.', exact=False)).to_be_visible()
            await playwright.expect(page.locator('.score-trend-chart')).to_have_count(0)
            periods = page.get_by_label('Период динамики')
            assert await periods.locator('option').all_text_contents() == ['3 дня', 'Неделя', 'Месяц', '3 месяца']
            for value in ['3d', '1w', '1m', '3m']:
                await periods.select_option(value)
                await playwright.expect(page.locator('.score-trend-chart')).to_have_count(0)
            assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            await page.screenshot(path=str(tmp_path / 'single-lesson.png'), full_page=True)
            await page.get_by_role('tab', name='Заключения', exact=True).click()
            await playwright.expect(page.get_by_role('heading', name='Заключение ещё не оформлено')).to_be_visible()
            await page.get_by_role('tab', name='Занятия', exact=True).click()
            await page.locator('.profile-history-link').first.click()
            await playwright.expect(page.get_by_role('heading', name='Оценки инструктора', exact=True)).to_be_visible()
            await playwright.expect(page.locator('.aux-skill-row').first.locator('strong')).to_have_text('3 / 4')
            await playwright.expect(page.get_by_role('link', name='Исправить отчёт')).to_have_count(0)
            await page.get_by_role('link', name='Профиль', exact=True).click()
            for label in ['Моя статистика', 'Время школы', 'О приложении']:
                await page.get_by_role('link', name=label, exact=False).click()
                await playwright.expect(page.get_by_role('heading', name=label, exact=True)).to_be_visible()
                if label == 'Моя статистика':
                    await playwright.expect(page.get_by_text('Нет оценок', exact=True)).to_have_count(0)
                if label == 'Время школы':
                    await playwright.expect(page.locator('time')).to_be_visible()
                await page.get_by_role('link', name='Профиль', exact=True).click()
            assert not errors, errors
        finally:
            await browser.close()


async def test_admin_reads_lesson_evidence_and_methodology(school):
    booking = await new_booking(school, context='Учебная площадка')
    await submit(school, booking)
    async with playwright.async_playwright() as engine:
        browser = await engine.chromium.launch()
        try:
            page, errors = await open_app(browser, school, '/clients/1', admin=True)
            await playwright.expect(page.get_by_role('heading', name='Прогресс ученика')).to_be_visible()
            await page.get_by_role('button', name='Открыть занятие').first.click()
            dialog = page.get_by_role('dialog')
            await playwright.expect(dialog).to_be_visible()
            await playwright.expect(dialog.get_by_text('3 / 4', exact=True).first).to_be_visible()
            await playwright.expect(dialog.get_by_text('Алексей Иванов', exact=True)).to_be_visible()
            await dialog.get_by_role('button', name='Закрыть', exact=True).click()
            await page.get_by_role('link', name='Настройки', exact=False).click()
            await playwright.expect(page.get_by_role('heading', name='Правила расчёта', exact=True)).to_be_visible()
            assert not errors, errors
        finally:
            await browser.close()


async def test_blank_report_requires_observations_and_preserves_zero(school):
    booking = await new_booking(school, context='Учебная площадка')
    await arrived_and_finished(school, booking)
    async with playwright.async_playwright() as engine:
        browser = await engine.chromium.launch()
        try:
            page, errors = await open_app(browser, school, '/report/' + str(booking['id']))
            save = page.get_by_role('button', name='Завершить отчёт', exact=True)
            await save.click()
            await playwright.expect(page.get_by_role('alert')).to_contain_text('Выберите хотя бы одно упражнение')
            await page.locator('.exercise-chip').first.click()
            await save.click()
            await playwright.expect(page.get_by_role('alert')).to_contain_text('Оцените хотя бы один навык')
            await page.locator('.skill-rating-item').first.get_by_role('button', name=': 0', exact=False).click()
            await save.click()
            await playwright.expect(page.get_by_role('alert')).to_contain_text('Укажите общую оценку')
            await page.get_by_role('group', name='Общая оценка занятия от 1 до 5').get_by_role('button', name='2', exact=True).click()
            await page.locator('.autonomy-pill').filter(has_text='A0').click()
            await page.get_by_label('Вмешательство инструктора', exact=False).select_option('нет')
            await save.click()
            await playwright.expect(page.get_by_role('heading', name='Отчёт сохранён!', exact=True)).to_be_visible()
            await page.get_by_role('link', name='Просмотреть сохранённый отчёт').click()
            await playwright.expect(page.locator('.aux-skill-row')).to_have_count(1)
            await playwright.expect(page.locator('.aux-skill-row strong')).to_have_text('0 / 4')
            profile = (await school['http'].get('/admin/clients/1/profile', headers=school['admin'])).json()
            assert profile['scores']['ground']['score'] == 0
            assert profile['scores']['city']['score'] is None
            assert len(profile['score_history']) == 1
            assert not errors, errors
        finally:
            await browser.close()
