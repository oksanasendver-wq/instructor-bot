"""Real ASGI requests, SQL and transactions, isolated from the working database."""

from datetime import datetime, timedelta
import pytest
from sqlalchemy import select, func
from app.models import Booking, LessonReport, ScoreSnapshot, Client

pytestmark = pytest.mark.asyncio


async def new_booking(school, **patch):
    body = {
        "client_id": 1,
        "instructor_id": 1,
        "date": "2026-09-06",
        "start_at": "11:00",
        "duration_minutes": 60,
        "context": "Город",
        "transmission": "АКПП",
        "payment_type": "наличные",
        "amount_due": 10000,
    }
    body.update(patch)
    r = await school["http"].post("/admin/bookings", json=body, headers=school["admin"])
    assert r.status_code == 200, r.text
    return r.json()["booking"]


async def report_input(
    school, context="Город", grade=3, physical=False, critical=False
):
    skills = (
        await school["http"].get(
            "/api/instructor/catalogs/skills",
            params={"context": context},
            headers=school["instructor"],
        )
    ).json()["skills"]
    exercises = (
        await school["http"].get(
            "/api/instructor/catalogs/exercises",
            params={"context": context},
            headers=school["instructor"],
        )
    ).json()["exercises"]
    return {
        "context": context,
        "skills": [{"skill_id": s["id"], "value": grade} for s in skills],
        "exercises": [{"exercise_id": exercises[0]["id"]}],
        "overall_grade_1_5": 4,
        "autonomy_level": "A3",
        "intervention": {
            "type": "физическое вмешательство" if physical else "нет",
            "is_critical": critical,
            "reason": "Пешеход / препятствие" if physical else None,
        },
        "comment_internal": "Работа с зеркалами",
    }


async def arrived_and_finished(school, b):
    http = school["http"]
    school["clock"]["now"] = datetime.fromisoformat(b["date"] + "T" + b["start_at"])
    r = await http.post(
        f"/api/instructor/bookings/{b['id']}/arrived", headers=school["instructor"]
    )
    assert r.status_code == 200, r.text
    school["clock"]["now"] = datetime.fromisoformat(
        b["date"] + "T" + b["end_at"]
    ) + timedelta(seconds=1)
    r = await http.post(
        f"/api/instructor/bookings/{b['id']}/finish", headers=school["instructor"]
    )
    assert r.status_code == 200, r.text


async def submit(school, b, body=None):
    await arrived_and_finished(school, b)
    body = body or await report_input(school, b["context"])
    response = await school["http"].post(
        f"/api/instructor/bookings/{b['id']}/report",
        json=body,
        headers=school["instructor"],
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_full_attendance_report_admin_profile_and_idempotency(school):
    http = school["http"]
    b = await new_booking(school)
    body = await report_input(school)
    result = await submit(school, b, body)
    assert result["scores"]["city"] == 75
    assert result["scores"]["ground"] is None and result["scores"]["overall"] is None
    r = await http.post(
        f"/api/instructor/bookings/{b['id']}/report",
        json=body,
        headers=school["instructor"],
    )
    assert r.status_code == 200 and r.json()["report_id"] == result["report_id"]
    async with school["sessions"]() as db:
        assert (
            await db.execute(select(func.count()).select_from(LessonReport))
        ).scalar() == 1
    profile = (
        await http.get("/admin/clients/1/profile", headers=school["admin"])
    ).json()
    assert (
        profile["stats"]["total_lessons"] == 1 and profile["stats"]["total_hours"] == 1
    )
    assert profile["history"][0]["comment_internal"] == "Работа с зеркалами"
    assert profile["history"][0]["exercises"]
    bookings = (await http.get("/admin/bookings", headers=school["admin"])).json()[
        "bookings"
    ]
    assert bookings[0]["payment_status"] == "pending"
    r = await http.post(
        f"/api/instructor/bookings/{b['id']}/payment",
        json={"received": True},
        headers=school["instructor"],
    )
    assert r.status_code == 200
    assert (await http.get("/admin/bookings", headers=school["admin"])).json()[
        "bookings"
    ][0]["payment_status"] == "received"


async def test_status_guards_and_no_show_does_not_score(school):
    http = school["http"]
    b = await new_booking(school)
    school["clock"]["now"] = datetime(2026, 9, 6, 10, 29)
    assert (
        await http.post(
            f"/api/instructor/bookings/{b['id']}/arrived", headers=school["instructor"]
        )
    ).status_code == 409
    school["clock"]["now"] = datetime(2026, 9, 6, 11, 30)
    assert (
        await http.post(
            f"/api/instructor/bookings/{b['id']}/no-show", headers=school["instructor"]
        )
    ).status_code == 409
    school["clock"]["now"] = datetime(2026, 9, 6, 12, 1)
    assert (
        await http.post(
            f"/api/instructor/bookings/{b['id']}/no-show", headers=school["instructor"]
        )
    ).status_code == 200
    assert (
        await http.post(
            f"/api/instructor/bookings/{b['id']}/arrived", headers=school["instructor"]
        )
    ).status_code == 409
    school["clock"]["now"] = datetime(2026, 9, 6, 13, 1)
    assert (
        await http.get("/api/instructor/clients", headers=school["instructor"])
    ).json() == []
    async with school["sessions"]() as db:
        assert (
            await db.execute(select(func.count()).select_from(ScoreSnapshot))
        ).scalar() == 0


async def test_attended_client_remains_available_to_own_instructor(school):
    http = school["http"]
    b = await new_booking(school)
    assert (
        await http.get(f"/api/instructor/bookings/{b['id']}", headers=school["other"])
    ).status_code == 404
    assert (
        await http.get("/api/instructor/clients/1/profile", headers=school["other"])
    ).status_code == 403
    await arrived_and_finished(school, b)
    school["clock"]["now"] = datetime(2026, 9, 6, 13)
    assert (
        await http.get(
            "/api/instructor/clients/1/profile", headers=school["instructor"]
        )
    ).status_code == 200
    clients = await http.get("/api/instructor/clients", headers=school["instructor"])
    assert clients.status_code == 200
    assert [client["id"] for client in clients.json()] == [1]
    assert (
        await http.get("/api/instructor/clients/1/profile", headers=school["other"])
    ).status_code == 403
    rows = (await http.get("/admin/bookings", headers=school["admin"])).json()[
        "bookings"
    ]
    assert rows[0]["status"] == "admin_review_required"
    grant = await http.post(
        "/admin/access-grants",
        json={"booking_id": b["id"], "reason": "Восстановлена связь", "minutes": 30},
        headers=school["admin"],
    )
    assert grant.status_code == 200, grant.text
    body = await report_input(school)
    assert (
        await http.post(
            f"/api/instructor/bookings/{b['id']}/report",
            json=body,
            headers=school["instructor"],
        )
    ).status_code == 200


async def test_invalid_input_and_conflicting_bookings(school):
    http = school["http"]
    b = await new_booking(school)
    collision = await http.post(
        "/admin/bookings",
        json={
            "client_id": 2,
            "instructor_id": 1,
            "date": "2026-09-06",
            "start_at": "11:30",
            "context": "Город",
            "transmission": "АКПП",
        },
        headers=school["admin"],
    )
    assert collision.status_code == 409
    invalid = await http.post(
        "/admin/clients",
        json={"full_name": " ", "phone": "bad"},
        headers=school["admin"],
    )
    assert invalid.status_code == 422
    await arrived_and_finished(school, b)
    body = await report_input(school)
    body["skills"][0]["value"] = 5
    assert (
        await http.post(
            f"/api/instructor/bookings/{b['id']}/report",
            json=body,
            headers=school["instructor"],
        )
    ).status_code == 422
    body = await report_input(school)
    body["skills"].append(body["skills"][0])
    assert (
        await http.post(
            f"/api/instructor/bookings/{b['id']}/report",
            json=body,
            headers=school["instructor"],
        )
    ).status_code == 422


async def test_rollback_if_scoring_fails(school, monkeypatch):
    from app.services.score_engine import ScoreEngine

    http = school["http"]
    b = await new_booking(school)
    await arrived_and_finished(school, b)
    body = await report_input(school)

    async def fail(*args, **kwargs):
        raise RuntimeError("scoring failed")

    monkeypatch.setattr(ScoreEngine, "recalculate", fail)
    with pytest.raises(RuntimeError):
        await http.post(
            f"/api/instructor/bookings/{b['id']}/report",
            json=body,
            headers=school["instructor"],
        )
    async with school["sessions"]() as db:
        assert (
            await db.execute(select(func.count()).select_from(LessonReport))
        ).scalar() == 0
        assert (await db.get(Booking, b["id"])).status == "assessment_required"


async def test_admin_correction_keeps_old_history_and_instructor_cannot_remove_critical(
    school,
):
    http = school["http"]
    b = await new_booking(school)
    body = await report_input(school, physical=True, critical=True)
    result = await submit(school, b, body)
    assert result["scores"]["city"] == 60
    body["intervention"] = {"type": "нет", "is_critical": False}
    rid = result["report_id"]
    assert (
        await http.patch(
            f"/api/instructor/reports/{rid}", json=body, headers=school["instructor"]
        )
    ).status_code == 403
    corrected = await http.patch(
        f"/admin/reports/{rid}",
        json={"report": body, "reason": "Ошибка выбора вмешательства"},
        headers=school["admin"],
    )
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["scores"]["city"] == 75
    logs = (await http.get("/admin/audit", headers=school["admin"])).json()
    assert any(
        l["action"] == "correct" and l["old"]["intervention"]["is_critical"]
        for l in logs
    )
    async with school["sessions"]() as db:
        assert (
            await db.execute(select(func.count()).select_from(ScoreSnapshot))
        ).scalar() == 6


async def test_expired_edit_blocked_but_admin_allowed(school):
    b = await new_booking(school)
    result = await submit(school, b)
    async with school["sessions"]() as db:
        report = await db.get(LessonReport, result["report_id"])
        report.edited_until = datetime.utcnow() - timedelta(seconds=1)
        await db.commit()
    body = await report_input(school)
    assert (
        await school["http"].patch(
            f"/api/instructor/reports/{result['report_id']}",
            json=body,
            headers=school["instructor"],
        )
    ).status_code == 403
    assert (
        await school["http"].patch(
            f"/admin/reports/{result['report_id']}",
            json={"report": body, "reason": "Уточнение оценки"},
            headers=school["admin"],
        )
    ).status_code == 200


async def test_flags_need_sustained_improvement_and_overall_needs_both_contexts(school):
    http = school["http"]
    for index, grade in enumerate([1, 1, 2, 3, 3, 3]):
        day = f"2026-09-{index + 1:02}"
        b = await new_booking(school, date=day)
        await submit(school, b, await report_input(school, grade=grade))
        flags = (
            await http.get("/admin/attention-flags", headers=school["admin"])
        ).json()
        if index in (2, 3, 4):
            assert len(flags) == 8
        if index == 5:
            assert len(flags) == 0
    profile = (
        await http.get("/admin/clients/1/profile", headers=school["admin"])
    ).json()
    assert profile["scores"]["overall"]["score"] is None
    for index in range(3):
        b = await new_booking(
            school, date=f"2026-09-{index + 7:02}", context="Учебная площадка"
        )
        await submit(school, b)
    profile = (
        await http.get("/admin/clients/1/profile", headers=school["admin"])
    ).json()
    assert profile["scores"]["overall"]["score"] == 75


async def test_catalogs_conclusions_and_archiving_keep_history(school):
    http = school["http"]
    b = await new_booking(school)
    await submit(school, b)
    item = await http.post(
        "/admin/catalogs/exercises",
        json={
            "context": "Город",
            "short_name": "Маршрут",
            "official_name": "Самостоятельный маршрут",
            "reason": "Новый маршрут",
        },
        headers=school["admin"],
    )
    assert item.status_code == 200
    for text in [
        "Рекомендуем продолжить занятия.",
        "Наблюдается положительная динамика.",
    ]:
        r = await http.post(
            "/admin/clients/1/conclusions",
            json={"status": "обучение рекомендуется продолжить", "text": text},
            headers=school["admin"],
        )
        assert r.status_code == 200, r.text
    profile = (
        await http.get("/admin/clients/1/profile", headers=school["admin"])
    ).json()
    assert [c["version"] for c in profile["conclusions"]] == [2, 1]
    assert (
        await http.delete("/admin/clients/1", headers=school["admin"])
    ).status_code == 200
    async with school["sessions"]() as db:
        assert (await db.get(Client, 1)).is_archived
        assert (
            await db.execute(select(func.count()).select_from(LessonReport))
        ).scalar() == 1
    assert len((await http.get("/admin/clients", headers=school["admin"])).json()) == 1

    archived = (
        await http.get("/admin/clients?archived=true", headers=school["admin"])
    ).json()
    assert len(archived) == 1 and archived[0]["id"] == 1
    assert (
        await http.post("/admin/clients/1/restore", headers=school["admin"])
    ).status_code == 200
    assert len((await http.get("/admin/clients", headers=school["admin"])).json()) == 2


async def test_unauthenticated_and_role_boundaries(school):
    for path in ("/api/instructor/me", "/admin/clients", "/admin/audit"):
        assert (await school["http"].get(path)).status_code == 401
    assert (
        await school["http"].get("/admin/clients", headers=school["instructor"])
    ).status_code == 403


async def test_ai_unconfigured_is_clear_and_does_not_mutate_scores(school):
    b = await new_booking(school)
    await submit(school, b)
    response = await school["http"].post(
        "/admin/clients/1/ai-draft", headers=school["admin"]
    )
    assert response.status_code == 503
    async with school["sessions"]() as db:
        assert (
            await db.execute(select(func.count()).select_from(ScoreSnapshot))
        ).scalar() == 3
