from app.core.time import utc_now

"""Attention flags use actual core-skill assessments and sustained recovery."""
from sqlalchemy import select
from app.models import AttentionFlag, SkillCatalog
from app.services.score_engine import ScoreEngine
from app.services.audit import audit_log


class AttentionFlagManager:
    def __init__(self, db):
        self.db = db

    async def check_and_update_flags(self, client_id, context, report_id):
        reports = await ScoreEngine(self.db).reports(client_id, context)
        skills = list(
            (
                await self.db.execute(
                    select(SkillCatalog).where(
                        SkillCatalog.context == context,
                        SkillCatalog.active.is_(True),
                        SkillCatalog.is_core.is_(True),
                    )
                )
            ).scalars()
        )
        active = list(
            (
                await self.db.execute(
                    select(AttentionFlag).where(
                        AttentionFlag.client_id == client_id,
                        AttentionFlag.context == context,
                        AttentionFlag.active.is_(True),
                    )
                )
            ).scalars()
        )
        unsafe = any(i.is_critical for r in reports[:3] for i in r.interventions)
        result = {"opened_flags": [], "closed_flags": []}
        checks = []
        for skill in skills:
            grades = [
                next(a.value_0_4 for a in r.skill_assessments if a.skill_id == skill.id)
                for r in reports
                if any(a.skill_id == skill.id for a in r.skill_assessments)
            ][:3]
            weights = [0.5, 0.3, 0.2][: len(grades)]
            level = (
                sum(g * w for g, w in zip(grades, weights)) / sum(weights)
                if grades
                else None
            )
            low = len(grades) >= 3 and (sum(g <= 1 for g in grades) >= 2 or level < 2)
            recovered = len(grades) == 3 and all(g >= 3 for g in grades) and not unsafe
            checks.append(
                (
                    skill.id,
                    low,
                    recovered,
                    f"{skill.name}: повторяющиеся трудности, последние оценки "
                    + ", ".join(map(str, grades)),
                )
            )
        # A separate safety flag for repeated physical/critical interventions.
        repeated = (
            sum(
                any(
                    i.is_critical or i.type == "физическое вмешательство"
                    for i in r.interventions
                )
                for r in reports[:3]
            )
            >= 2
        )
        safe_streak = len(reports) >= 3 and all(
            not any(
                i.is_critical or i.type == "физическое вмешательство"
                for i in r.interventions
            )
            for r in reports[:3]
        )
        checks.append(
            (
                None,
                repeated,
                safe_streak,
                "Повторяющиеся вмешательства: отработать безопасность",
            )
        )
        for skill_id, low, recovered, reason in checks:
            existing = next((f for f in active if f.skill_id == skill_id), None)
            if low and not existing:
                flag = AttentionFlag(
                    client_id=client_id,
                    context=context,
                    skill_id=skill_id,
                    reason=reason,
                )
                self.db.add(flag)
                await self.db.flush()
                await audit_log(
                    self.db,
                    "system",
                    0,
                    "attention_flag",
                    flag.id,
                    "open",
                    new_values={"reason": reason, "report_id": report_id},
                )
                result["opened_flags"].append(reason)
            if existing and recovered:
                existing.active = False
                existing.closed_at = utc_now()
                existing.closed_reason = (
                    "Три последовательные оценки не ниже 3 и нет критических событий"
                    if skill_id
                    else "Три последовательных безопасных занятия"
                )
                await audit_log(
                    self.db,
                    "system",
                    0,
                    "attention_flag",
                    existing.id,
                    "close",
                    new_values={
                        "reason": existing.closed_reason,
                        "report_id": report_id,
                    },
                )
                result["closed_flags"].append(existing.reason)
        await self.db.flush()
        return result

    async def get_active_flags(self, client_id, context=None):
        query = select(AttentionFlag).where(
            AttentionFlag.client_id == client_id, AttentionFlag.active.is_(True)
        )
        if context:
            query = query.where(AttentionFlag.context == context)
        return list(
            (
                await self.db.execute(query.order_by(AttentionFlag.opened_at.desc()))
            ).scalars()
        )
