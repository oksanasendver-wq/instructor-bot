"""Profiles expose real lesson evidence, without manufacturing progress."""

from datetime import datetime, timedelta
import pytest
from sqlalchemy import select
from app.models import ScoreSnapshot
from tests.integration.test_workflow import new_booking, report_input, submit

pytestmark = pytest.mark.asyncio


async def profile(school, actor="admin"):
    path = (
        "/admin/clients/1/profile"
        if actor == "admin"
        else "/api/instructor/clients/1/profile"
    )
    response = await school["http"].get(path, headers=school[actor])
    assert response.status_code == 200, response.text
    return response.json()


async def test_one_lesson_edits_do_not_create_progress_or_unassessed_scores(school):
    booking = await new_booking(school, context="Учебная площадка")
    result = await submit(school, booking)
    body = await report_input(school, context="Учебная площадка", grade=2)
    response = await school["http"].patch(
        f"/api/instructor/reports/{result['report_id']}",
        json=body,
        headers=school["instructor"],
    )
    assert response.status_code == 200, response.text
    data = await profile(school)
    assert data["scores"]["ground"]["score"] == 50
    assert data["scores"]["ground"]["delta"] is None
    for context in ("city", "overall"):
        assert data["scores"][context]["score"] is None
        assert data["scores"][context]["delta"] is None
        assert data["scores"][context]["details"] == {}
    assert len(data["score_history"]) == 1
    point = data["score_history"][0]
    assert point["booking_id"] == booking["id"]
    assert point["report_id"] == result["report_id"]
    assert point["date"] == "2026-09-06T12:00:00+05:00"
    assert point["score"] == 50
    assert data["history"][0]["skills"][0]["value"] == 2
    assert data["history"][0]["skills"][0]["name"]
    async with school["sessions"]() as db:
        snapshots = list((await db.execute(select(ScoreSnapshot))).scalars())
        assert len(snapshots) == 6  # The audit evidence remains append-only.


async def test_second_context_does_not_duplicate_first_context_progress(school):
    first = await new_booking(school, date="2026-09-01", context="Учебная площадка")
    await submit(school, first)
    second = await new_booking(school, date="2026-09-02", context="Город")
    await submit(school, second)
    data = await profile(school)
    assert len(data["score_history"]) == 2
    assert data["scores"]["ground"]["delta"] is None
    assert data["scores"]["city"]["delta"] is None
    third = await new_booking(school, date="2026-09-03", context="Учебная площадка")
    await submit(
        school, third, await report_input(school, context="Учебная площадка", grade=4)
    )
    data = await profile(school)
    assert len(data["score_history"]) == 3
    assert data["scores"]["ground"]["delta"] == 15.62
    assert [point["booking_id"] for point in data["score_history"]] == [
        first["id"],
        second["id"],
        third["id"],
    ]


async def test_other_author_report_is_readable_but_not_editable_for_assigned_instructor(
    school,
):
    first = await new_booking(school, date="2026-09-01")
    saved = await submit(school, first)
    report_path = f"/api/instructor/reports/{saved['report_id']}"
    assert (
        await school["http"].get(report_path, headers=school["other"])
    ).status_code in (403, 404)
    await new_booking(school, date="2026-09-07", instructor_id=2)
    detail = await school["http"].get(
        f"/api/instructor/bookings/{first['id']}", headers=school["other"]
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["actions"] == []
    assert detail.json()["can_edit_report"] is False
    report = await school["http"].get(report_path, headers=school["other"])
    assert report.status_code == 200, report.text
    assert report.json()["can_edit"] is False
    assert report.json()["skills"][0]["name"]
    assert report.json()["exercises"][0]["name"]
    assert report.json()["formula_version"] == 1
    assert (await profile(school, "other"))["history"][-1]["can_edit"] is False
    edit = await school["http"].patch(
        report_path, json=await report_input(school), headers=school["other"]
    )
    assert edit.status_code == 404
    # The owner retains read access after the editable interval expires.
    from app.models import LessonReport

    async with school["sessions"]() as db:
        stored = await db.get(LessonReport, saved["report_id"])
        stored.edited_until = datetime.utcnow() - timedelta(days=1)
        await db.commit()
    owner = await school["http"].get(report_path, headers=school["instructor"])
    assert owner.status_code == 200 and owner.json()["can_edit"] is False


async def test_catalog_revision_preserves_historical_names_scores_and_method(school):
    booking = await new_booking(school)
    await submit(school, booking)
    before = await profile(school)
    skill = before["history"][0]["skills"][0]
    response = await school["http"].patch(
        f"/admin/catalogs/skills/{skill['skill_id']}",
        json={
            "context": "Город",
            "name": "Новая редакция критерия",
            "weight": 50,
            "is_core": True,
            "reason": "Уточнение методики",
        },
        headers=school["admin"],
    )
    assert response.status_code == 200, response.text
    after = await profile(school)
    assert after["history"][0]["skills"][0]["name"] == skill["name"]
    assert after["history"][0]["skills"][0]["version"] == 1
    assert after["score_history"] == before["score_history"]
    ground = await new_booking(school, date="2026-09-07", context="Учебная площадка")
    await submit(school, ground)
    after = await profile(school)
    assert after["scores"]["city"]["formula_version"] == 1
    assert after["scores"]["ground"]["formula_version"] == 2
    city = await new_booking(school, date="2026-09-08")
    await submit(school, city)
    after = await profile(school)
    assert after["scores"]["city"]["formula_version"] == 2
    assert after["scores"]["city"]["delta"] is None


async def test_statistics_and_settings_use_real_instructor_data(school):
    empty = (
        await school["http"].get(
            "/api/instructor/me/statistics", headers=school["instructor"]
        )
    ).json()
    assert empty["total_lessons"] == 0 and empty["average_grade"] is None
    booking = await new_booking(school, context="Учебная площадка", duration_minutes=90)
    await submit(school, booking)
    data = (
        await school["http"].get(
            "/api/instructor/me/statistics", headers=school["instructor"]
        )
    ).json()
    assert (
        data["total_lessons"] == data["reported_lessons"] == data["total_clients"] == 1
    )
    assert data["ground_lessons"] == 1 and data["city_lessons"] == 0
    assert data["total_hours"] == 1.5 and data["average_grade"] == 4
    other = (
        await school["http"].get(
            "/api/instructor/me/statistics", headers=school["other"]
        )
    ).json()
    assert other["total_lessons"] == 0
    me = (
        await school["http"].get("/api/instructor/me", headers=school["instructor"])
    ).json()
    assert me["school_time"].endswith("+05:00") and me["app_version"]
    settings = (
        await school["http"].get("/admin/settings", headers=school["admin"])
    ).json()
    assert settings["score_methodology"]["version"] == 1
    assert settings["score_methodology"]["recency_weights"] == [0.5, 0.3, 0.2]
    assert settings["access_policy"]["edit_minutes_after"] == 30
    assert len(settings["conclusion_statuses"]) == 4
