from app.core.time import utc_now, as_utc

"""Validated reports: attendance, assessments, score and flags form one transaction."""
from datetime import timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator, field_validator
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.config import settings
from app.core.time import utc_iso
from app.models import (
    Instructor,
    Booking,
    LessonReport,
    LessonExercise,
    SkillAssessment,
    Intervention,
    ExerciseCatalog,
    SkillCatalog,
    Client,
    AuditLog,
)
from app.models.booking import Context
from app.models.lesson_report import AutonomyLevel, InterventionType
from app.api.instructor.dependencies import get_current_instructor
from app.services.score_engine import ScoreEngine
from app.services.attention_flag_manager import AttentionFlagManager
from app.services.audit import audit_log
from app.services.lifecycle import actions_for, has_booking_grant
from app.services.report_details import report_details

router = APIRouter()


class ExerciseInput(BaseModel):
    exercise_id: int = Field(gt=0)


class SkillInput(BaseModel):
    skill_id: int = Field(gt=0)
    value: int = Field(ge=0, le=4)


class InterventionInput(BaseModel):
    type: InterventionType = InterventionType.NONE
    reason: str | None = Field(default=None, max_length=255)
    is_critical: bool = False
    description: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def critical_reason(self):
        if self.type == InterventionType.PHYSICAL and not (self.reason or "").strip():
            raise ValueError("Укажите причину физического вмешательства")
        if self.is_critical and (
            self.type == InterventionType.NONE
            or not (self.description or self.reason or "").strip()
        ):
            raise ValueError(
                "Для критического события укажите вмешательство и краткое описание"
            )
        return self


class ReportCreateRequest(BaseModel):
    context: Context
    exercises: List[ExerciseInput] = Field(min_length=1, max_length=50)
    skills: List[SkillInput] = Field(min_length=1, max_length=50)
    overall_grade_1_5: int = Field(ge=1, le=5)
    autonomy_level: AutonomyLevel
    intervention: InterventionInput = Field(default_factory=InterventionInput)
    quick_verdict: str | None = Field(default=None, max_length=255)
    comment_internal: str | None = Field(default=None, max_length=500)

    @field_validator("autonomy_level", mode="before")
    @classmethod
    def expand_autonomy(cls, value):
        if value in AutonomyLevel.__members__:
            return AutonomyLevel[value]
        return value


async def validate_catalogs(db, request, booking):
    if request.context != booking.context:
        raise HTTPException(422, "Тип отчёта должен совпадать с типом занятия")
    skill_ids = [s.skill_id for s in request.skills]
    exercise_ids = [e.exercise_id for e in request.exercises]
    if len(set(skill_ids)) != len(skill_ids) or len(set(exercise_ids)) != len(
        exercise_ids
    ):
        raise HTTPException(422, "Навыки и упражнения не должны повторяться")
    skills = (
        (
            await db.execute(
                select(SkillCatalog).where(
                    SkillCatalog.context == request.context,
                    SkillCatalog.active.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    if not set(skill_ids).issubset({s.id for s in skills}):
        raise HTTPException(
            422, "Критерий недоступен для этого занятия. Обновите страницу"
        )
    exercises = (
        (
            await db.execute(
                select(ExerciseCatalog).where(
                    ExerciseCatalog.id.in_(exercise_ids),
                    ExerciseCatalog.context == request.context,
                    ExerciseCatalog.active.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    if len(exercises) != len(exercise_ids):
        raise HTTPException(422, "Упражнение недоступно для этого типа занятия")
    return skills, exercises


async def save_children(db, report, request, skills, exercises):
    versions = {s.id: s.version for s in skills}
    db.add_all(
        [
            LessonExercise(
                report_id=report.id,
                exercise_id=e.id,
                official_name_snapshot=e.official_name,
            )
            for e in exercises
        ]
    )
    db.add_all(
        [
            SkillAssessment(
                report_id=report.id,
                skill_id=s.skill_id,
                value_0_4=s.value,
                skill_version=versions[s.skill_id],
            )
            for s in request.skills
        ]
    )
    db.add(Intervention(report_id=report.id, **request.intervention.model_dump()))
    await db.flush()


async def finish_save(db, booking, report, instructor, action, request=None):
    await AttentionFlagManager(db).check_and_update_flags(
        booking.client_id, booking.context, report.id
    )
    scores = await ScoreEngine(db).recalculate(booking.client_id, report.id)
    await audit_log(
        db,
        "instructor",
        instructor.id,
        "report",
        report.id,
        action,
        new_values={
            "booking_id": booking.id,
            "scores": scores,
            "request": request.model_dump(mode="json") if request else None,
        },
    )
    await db.commit()
    return {
        "status": "ok",
        "report_id": report.id,
        "scores": scores,
        "edited_until": utc_iso(report.edited_until),
    }


@router.post("/bookings/{booking_id}/report")
async def create_report(
    booking_id: int,
    request: ReportCreateRequest,
    current_instructor: Instructor = Depends(get_current_instructor),
    db: AsyncSession = Depends(get_db),
):
    booking = (
        await db.execute(
            select(Booking)
            .where(
                Booking.id == booking_id, Booking.instructor_id == current_instructor.id
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not booking:
        raise HTTPException(404, "Занятие не найдено")
    if booking.status == "completed":
        existing = (
            await db.execute(
                select(LessonReport).where(LessonReport.booking_id == booking.id)
            )
        ).scalar_one_or_none()
        log = (
            (
                await db.execute(
                    select(AuditLog)
                    .where(
                        AuditLog.entity_type == "report",
                        AuditLog.entity_id == existing.id,
                        AuditLog.action == "create",
                    )
                    .order_by(AuditLog.id.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if existing
            else None
        )
        if log and log.new_json.get("request") == request.model_dump(mode="json"):
            return {
                "status": "ok",
                "report_id": existing.id,
                "scores": log.new_json["scores"],
                "edited_until": utc_iso(existing.edited_until),
            }
        raise HTTPException(409, "Отчёт уже сохранён. Откройте его для редактирования")
    if "report" not in await actions_for(db, booking):
        raise HTTPException(
            409,
            f"Сначала отметьте приход и завершите занятие. Отчёт доступен до {settings.PROFILE_MINUTES_AFTER} минут после окончания",
        )
    await db.execute(
        select(Client.id).where(Client.id == booking.client_id).with_for_update()
    )
    skills, exercises = await validate_catalogs(db, request, booking)
    report = LessonReport(
        booking_id=booking.id,
        instructor_id=current_instructor.id,
        **request.model_dump(exclude={"skills", "exercises", "intervention"}),
        edited_until=utc_now() + timedelta(minutes=settings.REPORT_EDIT_MINUTES),
    )
    db.add(report)
    await db.flush()
    await save_children(db, report, request, skills, exercises)
    booking.status = "completed"
    await db.flush()
    return await finish_save(db, booking, report, current_instructor, "create", request)


@router.get("/reports/{report_id}")
async def get_report(
    report_id: int,
    current_instructor: Instructor = Depends(get_current_instructor),
    db: AsyncSession = Depends(get_db),
):
    report = (
        await db.execute(
            select(LessonReport)
            .where(
                LessonReport.id == report_id,
            )
            .options(
                selectinload(LessonReport.booking),
                selectinload(LessonReport.skill_assessments),
                selectinload(LessonReport.exercises),
                selectinload(LessonReport.interventions),
            )
        )
    ).scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Отчёт не найден")
    booking = await db.get(Booking, report.booking_id)
    from app.services.access_control import AccessControl

    owned = report.instructor_id == current_instructor.id
    can_edit = owned and (
        bool(report.edited_until and utc_now() < as_utc(report.edited_until))
        or await has_booking_grant(db, booking)
    )
    if not can_edit and not await AccessControl(db).can_access_client(
        current_instructor.id, booking.client_id
    ):
        raise HTTPException(403, "Время доступа к отчёту истекло")
    return {
        "id": report.id,
        "booking_id": report.booking_id,
        "context": report.context,
        "overall_grade_1_5": report.overall_grade_1_5,
        "autonomy_level": report.autonomy_level,
        "comment_internal": report.comment_internal,
        "quick_verdict": report.quick_verdict,
        **(await report_details(db, [report]))[report.id],
        "intervention": {
            "type": report.interventions[0].type,
            "is_critical": report.interventions[0].is_critical,
            "reason": report.interventions[0].reason,
            "description": report.interventions[0].description,
        }
        if report.interventions
        else {"type": "нет"},
        "edited_until": utc_iso(report.edited_until),
        "can_edit": can_edit,
    }


@router.patch("/reports/{report_id}")
async def update_report(
    report_id: int,
    request: ReportCreateRequest,
    current_instructor: Instructor = Depends(get_current_instructor),
    db: AsyncSession = Depends(get_db),
):
    report = (
        await db.execute(
            select(LessonReport)
            .where(
                LessonReport.id == report_id,
                LessonReport.instructor_id == current_instructor.id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Отчёт не найден")
    booking = await db.get(Booking, report.booking_id)
    if (
        not report.edited_until or utc_now() >= as_utc(report.edited_until)
    ) and not await has_booking_grant(db, booking):
        raise HTTPException(
            403,
            f"Редактирование доступно {settings.REPORT_EDIT_MINUTES} минут после сохранения",
        )
    previous_events = (
        (
            await db.execute(
                select(Intervention).where(Intervention.report_id == report.id)
            )
        )
        .scalars()
        .all()
    )
    for event in previous_events:
        if (event.is_critical and not request.intervention.is_critical) or (
            event.type == "физическое вмешательство"
            and request.intervention.type != event.type
        ):
            raise HTTPException(
                403,
                "Исправить критическое или физическое вмешательство может только администратор с указанием причины",
            )
    previous_skills = (
        (
            await db.execute(
                select(SkillAssessment).where(SkillAssessment.report_id == report.id)
            )
        )
        .scalars()
        .all()
    )
    previous_exercises = (
        (
            await db.execute(
                select(LessonExercise).where(LessonExercise.report_id == report.id)
            )
        )
        .scalars()
        .all()
    )
    await audit_log(
        db,
        "instructor",
        current_instructor.id,
        "report",
        report.id,
        "before_update",
        old_values={
            "skills": [
                {"skill_id": a.skill_id, "value": a.value_0_4} for a in previous_skills
            ],
            "exercises": [{"exercise_id": e.exercise_id} for e in previous_exercises],
            "overall_grade": report.overall_grade_1_5,
            "autonomy": report.autonomy_level,
            "comment": report.comment_internal,
            "interventions": [
                {
                    "type": e.type,
                    "critical": e.is_critical,
                    "reason": e.reason,
                    "description": e.description,
                }
                for e in previous_events
            ],
        },
    )
    await db.execute(
        select(Client.id).where(Client.id == booking.client_id).with_for_update()
    )
    skills, exercises = await validate_catalogs(db, request, booking)
    for key, value in request.model_dump(
        exclude={"skills", "exercises", "intervention"}
    ).items():
        setattr(report, key, value)
    report.last_edited_at = utc_now()
    for model in (LessonExercise, SkillAssessment, Intervention):
        await db.execute(delete(model).where(model.report_id == report.id))
    await save_children(db, report, request, skills, exercises)
    return await finish_save(db, booking, report, current_instructor, "update", request)
