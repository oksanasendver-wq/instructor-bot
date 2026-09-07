from app.core.time import utc_now

"""Audited corrections, access grants, conclusions and school configuration."""
from datetime import timedelta
from typing import Literal, get_args
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.core.time import utc_iso
from app.models import (
    Booking,
    Client,
    Instructor,
    LessonReport,
    SkillAssessment,
    LessonExercise,
    Intervention,
    AccessGrant,
    AuditLog,
    FinalConclusion,
    AIDraft,
    ScoreFormulaVersion,
)
from app.api.admin.dependencies import get_current_admin
from app.api.instructor.reports import (
    ReportCreateRequest,
    validate_catalogs,
    save_children,
)
from app.services.audit import audit_log
from app.services.score_engine import ScoreEngine, RECENCY_WEIGHTS
from app.services.attention_flag_manager import AttentionFlagManager
from app.services.report_details import report_details

router = APIRouter()


async def report_payload(db, report_id):
    r = (
        await db.execute(
            select(LessonReport)
            .where(LessonReport.id == report_id)
            .options(
                selectinload(LessonReport.booking),
                selectinload(LessonReport.skill_assessments),
                selectinload(LessonReport.exercises),
                selectinload(LessonReport.interventions),
            )
        )
    ).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Отчёт не найден")
    return r, {
        "id": r.id,
        "booking_id": r.booking_id,
        "context": r.context,
        "overall_grade_1_5": r.overall_grade_1_5,
        "autonomy_level": r.autonomy_level,
        "comment_internal": r.comment_internal,
        "quick_verdict": r.quick_verdict,
        **(await report_details(db, [r]))[r.id],
        "intervention": {
            "type": r.interventions[0].type,
            "reason": r.interventions[0].reason,
            "is_critical": r.interventions[0].is_critical,
            "description": r.interventions[0].description,
        }
        if r.interventions
        else {"type": "нет", "is_critical": False},
    }


@router.get("/reports/{report_id}")
async def get_report(
    report_id: int,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return (await report_payload(db, report_id))[1]


class ReportCorrection(BaseModel):
    report: ReportCreateRequest
    reason: str = Field(min_length=3, max_length=1000)


@router.patch("/reports/{report_id}")
async def correct_report(
    report_id: int,
    request: ReportCorrection,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        select(LessonReport.id).where(LessonReport.id == report_id).with_for_update()
    )
    report, old = await report_payload(db, report_id)
    booking = await db.get(Booking, report.booking_id)
    await db.execute(
        select(Client.id).where(Client.id == booking.client_id).with_for_update()
    )
    previous_context = booking.context
    booking.context = request.report.context
    skills, exercises = await validate_catalogs(db, request.report, booking)
    for key, value in request.report.model_dump(
        exclude={"skills", "exercises", "intervention"}
    ).items():
        setattr(report, key, value)
    report.last_edited_at = utc_now()
    await audit_log(
        db,
        "admin",
        0,
        "report",
        report.id,
        "correct",
        old_values=old,
        new_values=request.report.model_dump(mode="json"),
        reason=request.reason,
    )
    for model in (SkillAssessment, LessonExercise, Intervention):
        await db.execute(delete(model).where(model.report_id == report_id))
    await save_children(db, report, request.report, skills, exercises)
    # Expire loaded child collections before recalculation.
    db.expire(report, ["skill_assessments", "interventions", "exercises"])
    await AttentionFlagManager(db).check_and_update_flags(
        booking.client_id, booking.context, report.id
    )
    if previous_context != booking.context:
        await AttentionFlagManager(db).check_and_update_flags(
            booking.client_id, previous_context, report.id
        )
    scores = await ScoreEngine(db).recalculate(booking.client_id, report.id)
    await db.commit()
    return {"status": "ok", "report_id": report.id, "scores": scores}


class GrantInput(BaseModel):
    booking_id: int = Field(gt=0)
    minutes: int = Field(default=30, ge=5, le=240)
    reason: str = Field(min_length=3, max_length=1000)
    confirm_attended: bool = False


@router.post("/access-grants")
async def grant_access(
    request: GrantInput,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    booking = (
        await db.execute(
            select(Booking).where(Booking.id == request.booking_id).with_for_update()
        )
    ).scalar_one_or_none()
    if not booking:
        raise HTTPException(404, "Занятие не найдено")
    instructor = await db.get(Instructor, booking.instructor_id)
    if not instructor.is_active:
        raise HTTPException(422, "Сначала активируйте инструктора")
    if booking.status != "completed":
        if (
            not booking.arrived_at
            and booking.status not in ("in_progress", "assessment_required")
            and not request.confirm_attended
        ):
            raise HTTPException(422, "Подтвердите, что занятие фактически состоялось")
        if request.confirm_attended and not booking.arrived_at:
            booking.arrived_at = utc_now()
        booking.status = "assessment_required"
    now = utc_now()
    grant = AccessGrant(
        booking_id=booking.id,
        instructor_id=booking.instructor_id,
        client_id=booking.client_id,
        valid_from=now,
        valid_until=now + timedelta(minutes=request.minutes),
        reason=request.reason,
        granted_by_admin_id=0,
    )
    db.add(grant)
    await db.flush()
    await audit_log(
        db,
        "admin",
        0,
        "booking",
        booking.id,
        "grant_access",
        new_values={
            "grant_id": grant.id,
            "until": utc_iso(grant.valid_until),
            "confirmed_attendance": request.confirm_attended,
        },
        reason=request.reason,
    )
    await db.commit()
    return {"status": "ok", "valid_until": utc_iso(grant.valid_until)}


class ConclusionInput(BaseModel):
    status: Literal[
        "обучение рекомендуется продолжить",
        "к самостоятельному управлению пока не готов",
        "уровень достаточный, но имеются обязательные рекомендации",
        "готов к самостоятельному управлению",
    ]
    text: str = Field(min_length=10, max_length=10000)
    ai_draft_id: int | None = None
    approved_by_type: Literal["admin", "instructor"] = "admin"
    approved_by_id: int = 0


@router.post("/clients/{client_id}/conclusions")
async def save_conclusion(
    client_id: int,
    request: ConclusionInput,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    client = (
        await db.execute(select(Client).where(Client.id == client_id).with_for_update())
    ).scalar_one_or_none()
    if not client:
        raise HTTPException(404, "Ученик не найден")
    if request.ai_draft_id:
        draft = await db.get(AIDraft, request.ai_draft_id)
        if not draft or draft.client_id != client_id:
            raise HTTPException(422, "Черновик не принадлежит этому ученику")
    if request.approved_by_type == "instructor" and not await db.get(
        Instructor, request.approved_by_id
    ):
        raise HTTPException(422, "Инструктор не найден")
    version = (
        await db.execute(
            select(func.max(FinalConclusion.version)).where(
                FinalConclusion.client_id == client_id
            )
        )
    ).scalar() or 0
    conclusion = FinalConclusion(
        client_id=client_id, version=version + 1, **request.model_dump()
    )
    db.add(conclusion)
    await db.flush()
    await audit_log(
        db,
        "admin",
        0,
        "conclusion",
        conclusion.id,
        "approve",
        new_values=request.model_dump(),
        reason="Утверждена версия " + str(version + 1),
    )
    await db.commit()
    return {"id": conclusion.id, "version": conclusion.version}


@router.get("/audit")
async def audit(
    entity_type: str | None = None,
    entity_id: int | None = None,
    limit: int = Query(100, ge=1, le=500),
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditLog)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)
    rows = (await db.execute(query.order_by(AuditLog.id.desc()).limit(limit))).scalars()
    return [
        {
            "id": r.id,
            "actor_type": r.actor_type,
            "actor_id": r.actor_id,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "action": r.action,
            "old": r.old_json,
            "new": r.new_json,
            "reason": r.reason,
            "created_at": utc_iso(r.created_at),
        }
        for r in rows
    ]


@router.get("/settings")
async def configuration(
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    formula = (
        await db.execute(
            select(ScoreFormulaVersion)
            .where(ScoreFormulaVersion.valid_from <= utc_now())
            .order_by(ScoreFormulaVersion.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return {
        "timezone": settings.TIMEZONE,
        "access_policy": {
            "arrival_minutes_before": settings.ARRIVAL_MINUTES_BEFORE,
            "profile_minutes_after": settings.PROFILE_MINUTES_AFTER,
            "edit_minutes_after": settings.REPORT_EDIT_MINUTES,
        },
        "conclusion_statuses": list(
            get_args(ConclusionInput.model_fields["status"].annotation)
        ),
        "score_methodology": {
            "version": formula.version,
            "valid_from": utc_iso(formula.valid_from),
            "ground_weights": formula.ground_weights_json,
            "city_weights": formula.city_weights_json,
            "overall_weights": formula.overall_weights_json,
            "caps": formula.caps_json,
            "recency_weights": formula.caps_json.get(
                "recency_weights", RECENCY_WEIGHTS
            ),
        }
        if formula
        else None,
        "ai_provider": settings.AI_PROVIDER,
        "ai_model": settings.GROQ_MODEL
        if settings.AI_PROVIDER == "groq"
        else settings.NVIDIA_MODEL,
        "ai_configured": bool(
            settings.GROQ_API_KEY
            if settings.AI_PROVIDER == "groq"
            else settings.NVIDIA_API_KEY
        ),
        "webhook_configured": bool(settings.TELEGRAM_WEBHOOK_SECRET),
        "instruction": "Провайдер, модель и ключи задаются в переменных окружения backend. Ключи не передаются в браузер.",
    }
