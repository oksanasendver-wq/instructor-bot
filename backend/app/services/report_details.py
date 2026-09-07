"""Read report evidence using the criterion version saved with each assessment."""

from sqlalchemy import select
from app.core.time import utc_iso
from app.models import SkillCatalog, ScoreFormulaVersion, ScoreSnapshot


async def report_details(db, reports, snapshots=None):
    reports = [report for report in reports if report is not None]
    if not reports:
        return {}
    versions = {}
    for skill in (await db.execute(select(SkillCatalog))).scalars():
        versions[(skill.id, skill.version)] = skill.name
    for formula in (
        await db.execute(
            select(ScoreFormulaVersion).order_by(ScoreFormulaVersion.version)
        )
    ).scalars():
        for weights in (formula.ground_weights_json, formula.city_weights_json):
            for key, skill in (weights or {}).items():
                if isinstance(skill, dict) and skill.get("name"):
                    versions[(int(key), skill.get("version", 1))] = skill["name"]
    if snapshots is None:
        snapshots = list(
            (
                await db.execute(
                    select(ScoreSnapshot)
                    .where(ScoreSnapshot.client_id == reports[0].booking.client_id)
                    .order_by(
                        ScoreSnapshot.calculated_at.desc(), ScoreSnapshot.id.desc()
                    )
                )
            ).scalars()
        )
    report_versions = {}
    for snapshot in snapshots:
        source_id = (snapshot.inputs_json or {}).get("source_report_id")
        if source_id is not None:
            report_versions.setdefault(source_id, snapshot.formula_version)
    return {
        report.id: {
            "skills": [
                {
                    "skill_id": assessment.skill_id,
                    "value": assessment.value_0_4,
                    "name": versions.get(
                        (assessment.skill_id, assessment.skill_version)
                    ),
                    "version": assessment.skill_version,
                }
                for assessment in report.skill_assessments
            ],
            "exercises": [
                {
                    "exercise_id": exercise.exercise_id,
                    "name": exercise.official_name_snapshot,
                }
                for exercise in report.exercises
            ],
            "interventions": [
                {
                    "type": event.type,
                    "reason": event.reason,
                    "description": event.description,
                    "is_critical": event.is_critical,
                }
                for event in report.interventions
            ],
            "created_at": utc_iso(report.created_at),
            "last_edited_at": utc_iso(report.last_edited_at),
            "formula_version": report_versions.get(report.id),
        }
        for report in reports
    }
