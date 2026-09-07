"""Exact numeric expectations from NEW_TZ, including sparse assessments."""

from types import SimpleNamespace as Obj
import pytest
from app.services.score_engine import calculate_reports


def skill(id=1, weight=100, core=True):
    return Obj(id=id, name="Навык", weight=weight, is_core=core, version=1)


def report(id=1, grade=4, autonomy="A3", physical=False, critical=False, grades=None):
    return Obj(
        id=id,
        autonomy_level=autonomy,
        skill_assessments=[
            Obj(skill_id=k, value_0_4=v) for k, v in (grades or {1: grade}).items()
        ],
        interventions=[
            Obj(
                type="физическое вмешательство" if physical else "нет",
                is_critical=critical,
                reason="Причина",
            )
        ],
    )


def test_recency_normalization():
    assert (
        calculate_reports([report(grade=4), report(grade=0)], [skill()], "Город")[
            "score"
        ]
        == 62.5
    )


def test_three_assessment_weights():
    assert (
        calculate_reports(
            [report(grade=4), report(grade=2), report(grade=0)], [skill()], "Город"
        )["score"]
        == 65
    )


def test_skipped_skill_uses_last_three_actual_grades():
    reports = [
        report(4, grades={2: 4}),
        report(3, grades={1: 4}),
        report(2, grades={1: 2}),
        report(1, grades={1: 0}),
    ]
    data = calculate_reports(reports, [skill(), skill(2)], "Город")
    assert data["details"]["skills"][0]["level"] == 65


def test_criterion_weights():
    data = calculate_reports(
        [report(grades={1: 4, 2: 0})], [skill(1, 75), skill(2, 25)], "Город"
    )
    assert data["score"] == 75


@pytest.mark.parametrize(
    "autonomy,cap", [("A0", 55), ("A1", 70), ("A2", 85), ("A3", 100)]
)
def test_autonomy_caps(autonomy, cap):
    assert (
        calculate_reports([report(autonomy=autonomy)], [skill()], "Город")["score"]
        == cap
    )


def test_repeated_physical_is_stricter_than_single_critical():
    assert (
        calculate_reports(
            [report(physical=True, critical=True), report(physical=True)],
            [skill()],
            "Город",
        )["score"]
        == 50
    )
    assert calculate_reports([report(critical=True)], [skill()], "Город")["score"] == 60
    assert calculate_reports([report(physical=True)], [skill()], "Город")["score"] == 70


def test_caps_expire_after_three_safe_context_lessons():
    assert (
        calculate_reports(
            [report(), report(), report(), report(critical=True)], [skill()], "Город"
        )["score"]
        == 100
    )


def test_reliability_requires_two_assessments_of_eighty_percent_core():
    scores = calculate_reports(
        [report(), report(), report()], [skill(), skill(2)], "Город"
    )
    assert scores["status"] == "Формируется"
    assert (
        calculate_reports([report(), report(), report()], [skill()], "Город")["status"]
        == "Достоверный"
    )


def test_no_data_is_not_zero():
    assert calculate_reports([], [skill()], "Город")["score"] is None
    assert calculate_reports([report(grade=0)], [skill()], "Город")["score"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "count,missing_core,unsafe,flag,expected",
    [
        (5, False, False, False, 100),
        (4, False, False, False, 99),
        (5, True, False, False, 99),
        (5, False, True, False, 70),
        (5, False, False, True, 99),
    ],
)
async def test_overall_hundred_requires_every_perfect_condition(
    count, missing_core, unsafe, flag, expected
):
    from unittest.mock import AsyncMock
    from app.services.score_engine import ScoreEngine

    db = AsyncMock()
    db.execute.return_value = Obj(scalar_one_or_none=lambda: 1 if flag else None)
    engine = ScoreEngine(db)
    engine.reports = AsyncMock(return_value=[report(critical=unsafe)])
    data = {
        "score": 100,
        "status": "Достоверный",
        "details": {
            "lessons_count": count,
            "core_count": 2 if missing_core else 1,
            "skills": [{"is_core": True, "values": [4, 4, 4]}],
            "autonomy": ["A3"] * 3,
        },
    }
    assert (await engine.calculate_school_readiness(1, data, data))["score"] == expected
