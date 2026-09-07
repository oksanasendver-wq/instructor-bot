"""Versioned, explainable scoring from the last three actual assessments per skill."""

from collections import Counter
from types import SimpleNamespace
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import (
    Booking,
    Client,
    LessonReport,
    SkillCatalog,
    ScoreSnapshot,
    ScoreFormulaVersion,
    AttentionFlag,
)
from app.core.time import utc_now

CONTEXTS = {"training_ground": "Учебная площадка", "city": "Город"}
RECENCY_WEIGHTS = [0.5, 0.3, 0.2]
DEFAULT_CAPS = {
    "autonomy": {"A0": 55, "A1": 70, "A2": 85, "A3": 100},
    "physical": 70,
    "critical": 60,
    "repeated_physical": 50,
    "overall_critical_last_10": 70,
}


def calculate_reports(reports, skills, context, caps=None):
    caps = caps or DEFAULT_CAPS
    if not reports:
        return {
            "score": None,
            "status": "Недостаточно данных",
            "details": {"lessons_count": 0, "skills": []},
        }
    levels = []
    for skill in skills:
        grades = [
            next(a.value_0_4 for a in r.skill_assessments if a.skill_id == skill.id)
            for r in reports
            if any(a.skill_id == skill.id for a in r.skill_assessments)
        ][:3]
        if not grades:
            continue
        weights = caps.get("recency_weights", RECENCY_WEIGHTS)[: len(grades)]
        level = sum(v * 25 * w for v, w in zip(grades, weights)) / sum(weights)
        levels.append(
            {
                "id": skill.id,
                "name": skill.name,
                "weight": float(skill.weight),
                "is_core": skill.is_core,
                "version": skill.version,
                "values": grades,
                "level": round(level, 2),
            }
        )
    if not levels:
        return {
            "score": None,
            "status": "Недостаточно данных",
            "details": {"lessons_count": 0, "skills": []},
        }
    base = sum(s["level"] * s["weight"] for s in levels) / sum(
        s["weight"] for s in levels
    )
    recent = reports[:3]
    autonomy = [
        getattr(r.autonomy_level, "value", r.autonomy_level).split(" ")[0]
        for r in recent
    ]
    # A frequency tie is resolved by the most recent lesson, deterministically.
    predominant = Counter(autonomy).most_common(1)[0][0]
    autonomy_cap = caps["autonomy"][predominant]
    events = [i for r in recent for i in r.interventions]
    physical = sum(i.type == "физическое вмешательство" for i in events)
    critical = any(i.is_critical for i in events)
    safety_cap = min(
        caps["physical"] if physical else 100,
        caps["critical"] if critical else 100,
        caps["repeated_physical"] if physical >= 2 else 100,
    )
    core = [s for s in skills if s.is_core]
    repeated = sum(s["is_core"] and len(s["values"]) >= 2 for s in levels)
    coverage = (
        repeated / len(core)
        if core
        else sum(len(s["values"]) >= 2 for s in levels) / len(skills)
    )
    status = "Предварительный" if len(reports) == 1 else "Формируется"
    if len(reports) >= 3 and coverage >= 0.8:
        status = "Достоверный"
    return {
        "score": round(min(base, autonomy_cap, safety_cap), 2),
        "status": status,
        "details": {
            "base_score": round(base, 2),
            "autonomy_cap": autonomy_cap,
            "safety_cap": safety_cap,
            "lessons_count": len(reports),
            "skill_coverage": round(coverage * 100),
            "core_count": len(core),
            "skills": levels,
            "autonomy": autonomy,
            "report_ids": [r.id for r in recent],
            "evaluated_report_id": reports[0].id,
            "critical_events": [
                {
                    "report_id": r.id,
                    "type": i.type,
                    "reason": i.reason,
                    "critical": i.is_critical,
                }
                for r in recent
                for i in r.interventions
                if i.type != "нет"
            ],
        },
    }


class ScoreEngine:
    def __init__(self, db):
        self.db = db

    async def reports(self, client_id, context=None):
        query = (
            select(LessonReport)
            .join(Booking)
            .where(Booking.client_id == client_id, Booking.status == "completed")
        )
        if context:
            query = query.where(LessonReport.context == context)
        return list(
            (
                await self.db.execute(
                    query.options(
                        selectinload(LessonReport.skill_assessments),
                        selectinload(LessonReport.interventions),
                    )
                    .execution_options(populate_existing=True)
                    .order_by(
                        Booking.date.desc(),
                        Booking.start_at.desc(),
                        LessonReport.id.desc(),
                    )
                )
            ).scalars()
        )

    async def calculate_context_score(self, client_id, context, formula=None):
        label = CONTEXTS.get(context, context)
        reports = await self.reports(client_id, label)
        if formula:
            weights = (
                formula.ground_weights_json
                if label == CONTEXTS["training_ground"]
                else formula.city_weights_json
            )
            skills = [SimpleNamespace(**item) for item in weights.values()]
        else:
            skills = list(
                (
                    await self.db.execute(
                        select(SkillCatalog)
                        .where(
                            SkillCatalog.context == label, SkillCatalog.active.is_(True)
                        )
                        .order_by(SkillCatalog.sort_order)
                    )
                ).scalars()
            )
        return calculate_reports(
            reports, skills, label, formula.caps_json if formula else None
        )

    async def calculate_school_readiness(
        self, client_id, ground=None, city=None, formula=None
    ):
        ground = ground or await self.calculate_context_score(
            client_id, "training_ground"
        )
        city = city or await self.calculate_context_score(client_id, "city")
        if ground["status"] != "Достоверный" or city["status"] != "Достоверный":
            return None
        recent = (await self.reports(client_id))[:10]
        unsafe = any(
            i.type == "физическое вмешательство" or i.is_critical
            for r in recent
            for i in r.interventions
        )
        overall_cap = (
            (formula.caps_json if formula else DEFAULT_CAPS)["overall_critical_last_10"]
            if any(i.is_critical for r in recent for i in r.interventions)
            else 100
        )
        has_flags = (
            await self.db.execute(
                select(AttentionFlag.id)
                .where(
                    AttentionFlag.client_id == client_id, AttentionFlag.active.is_(True)
                )
                .limit(1)
            )
        ).scalar_one_or_none() is not None
        perfect = all(
            data["details"]["lessons_count"] >= 5
            and sum(s["is_core"] for s in data["details"]["skills"])
            == data["details"]["core_count"]
            and all(
                s["values"] == [4, 4, 4]
                for s in data["details"]["skills"]
                if s["is_core"]
            )
            and data["details"]["autonomy"] == ["A3"] * 3
            for data in (ground, city)
        )
        perfect = (
            perfect
            and not unsafe
            and not has_flags
            and ground["score"] == city["score"] == 100
        )
        weights = (
            formula.overall_weights_json
            if formula
            else {"training_ground": 0.4, "city": 0.6}
        )
        value = min(
            overall_cap,
            round(
                ground["score"] * weights["training_ground"]
                + city["score"] * weights["city"]
            ),
        )
        if value == 100 and not perfect:
            value = 99
        return {
            "score": value,
            "status": "Достоверный",
            "details": {
                "formula": f"{weights['training_ground'] * 100:g}% площадка + {weights['city'] * 100:g}% город",
                "safety_cap": overall_cap,
                "perfect_conditions_met": perfect,
                "ground": ground["score"],
                "city": city["score"],
                "evaluated_report_id": recent[0].id if recent else None,
                "report_ids": [report.id for report in recent],
            },
        }

    async def save_snapshot(
        self, client_id, context, score_data, report_id=None, version=1
    ):
        # Append-only snapshots preserve both formula changes and report corrections.
        snapshot = ScoreSnapshot(
            client_id=client_id,
            context=context,
            score=score_data["score"] or 0,
            status=score_data["status"],
            formula_version=version,
            inputs_json={
                **score_data["details"],
                "source_report_id": report_id,
                "score": score_data["score"],
            },
            caps_json={
                k: score_data["details"].get(k) for k in ("safety_cap", "autonomy_cap")
            },
        )
        self.db.add(snapshot)
        await self.db.flush()
        return snapshot

    async def recalculate(self, client_id, report_id):
        await self.db.execute(
            select(Client.id).where(Client.id == client_id).with_for_update()
        )
        formula = (
            await self.db.execute(
                select(ScoreFormulaVersion)
                .where(ScoreFormulaVersion.valid_from <= utc_now())
                .order_by(ScoreFormulaVersion.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        version = formula.version if formula else 1
        ground = await self.calculate_context_score(
            client_id, "training_ground", formula
        )
        city = await self.calculate_context_score(client_id, "city", formula)
        overall = await self.calculate_school_readiness(
            client_id, ground, city, formula
        )
        empty = {
            "score": None,
            "status": "Недостаточно данных",
            "details": {"message": "Нужны достоверные оценки площадки и города"},
        }
        for context, data in [
            ("training_ground", ground),
            ("city", city),
            ("overall", overall or empty),
        ]:
            await self.save_snapshot(client_id, context, data, report_id, version)
        return {
            "ground": ground["score"],
            "city": city["score"],
            "overall": overall["score"] if overall else None,
        }
