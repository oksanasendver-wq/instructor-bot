from app.core.time import utc_now, as_utc

"""One profile projection shared by the mini app and administration."""
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from app.models import (
    Client,
    Booking,
    LessonReport,
    Instructor,
    ScoreSnapshot,
    AttentionFlag,
    FinalConclusion,
)
from app.core.time import utc_iso, booking_window
from app.core.config import settings
from app.services.report_details import report_details
from app.services.lifecycle import has_booking_grant


def score_projection(snapshots, rows):
    """A correction is a revision of evidence, never another attended lesson."""
    reports = {
        report.id: (booking, report)
        for booking, _, report in rows
        if report and booking.status == "completed" and report.skill_assessments
    }
    contexts = {"training_ground": "Учебная площадка", "city": "Город"}
    series = {context: {} for context in (*contexts, "overall")}
    latest = {}
    for snapshot in snapshots:
        context = snapshot.context
        if context not in series:
            continue
        inputs = snapshot.inputs_json or {}
        source = reports.get(inputs.get("source_report_id"))
        # Recalculating all contexts after a city report does not turn that report
        # into new evidence for the training ground (or change its old method).
        if context in contexts and source and source[1].context != contexts[context]:
            continue
        report_ids = inputs.get("report_ids") or []
        evaluated_id = inputs.get("evaluated_report_id")
        if evaluated_id is None:
            evaluated_id = (
                report_ids[0] if report_ids else inputs.get("source_report_id")
            )
        if evaluated_id not in reports:
            continue
        booking, report = reports[evaluated_id]
        if context in contexts and report.context != contexts[context]:
            continue
        if context == "overall" and not all(
            any(r.context == label for _, r in reports.values())
            for label in contexts.values()
        ):
            continue
        latest.setdefault(context, snapshot)
        # First snapshot in this descending list is the latest saved revision.
        if evaluated_id in series[context]:
            continue
        series[context][evaluated_id] = None
        if (
            snapshot.status == "Недостаточно данных"
            or inputs.get("score", snapshot.score) is None
        ):
            continue
        _, end = booking_window(booking)
        series[context][evaluated_id] = {
            "score": float(snapshot.score),
            "context": context,
            "date": end.replace(tzinfo=ZoneInfo(settings.TIMEZONE)).isoformat(),
            "booking_id": booking.id,
            "report_id": evaluated_id,
            "status": snapshot.status,
            "formula_version": snapshot.formula_version,
            "calculated_at": utc_iso(snapshot.calculated_at),
        }
    scores = {}
    history = []
    for key, context in [
        ("ground", "training_ground"),
        ("city", "city"),
        ("overall", "overall"),
    ]:
        points = sorted(
            [point for point in series[context].values() if point],
            key=lambda point: (point["date"], point["booking_id"]),
        )
        last = latest.get(context)
        valid = (
            last
            and last.status != "Недостаточно данных"
            and (last.inputs_json or {}).get("score", last.score) is not None
        )
        delta = None
        if (
            valid
            and len(points) >= 2
            and points[-1]["formula_version"] == points[-2]["formula_version"]
        ):
            delta = round(points[-1]["score"] - points[-2]["score"], 2)
        scores[key] = {
            "score": float(last.score) if valid else None,
            "status": last.status if last else "Нет данных",
            "details": last.inputs_json if last else {},
            "delta": delta,
            "formula_version": last.formula_version if last else None,
            "calculated_at": utc_iso(last.calculated_at) if last else None,
        }
        history.extend(points)
    return scores, sorted(
        history,
        key=lambda point: (point["date"], point["booking_id"], point["context"]),
    )


def flag_payload(flag, client=None):
    return {
        "id": flag.id,
        "client_id": flag.client_id,
        "client_name": client.full_name if client else None,
        "context": flag.context,
        "reason": flag.reason,
        "active": flag.active,
        "opened_at": utc_iso(flag.opened_at),
        "closed_at": utc_iso(flag.closed_at),
        "closed_reason": flag.closed_reason,
    }


async def client_profile(db, client_id, admin=False, instructor_id=None):
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(404, "Ученик не найден")
    rows = (
        await db.execute(
            select(Booking, Instructor, LessonReport)
            .select_from(Booking)
            .join(Instructor, Booking.instructor_id == Instructor.id)
            .outerjoin(LessonReport, LessonReport.booking_id == Booking.id)
            .where(Booking.client_id == client_id)
            .options(
                selectinload(LessonReport.skill_assessments),
                selectinload(LessonReport.interventions),
                selectinload(LessonReport.exercises),
            )
            .order_by(Booking.date.desc(), Booking.start_at.desc())
        )
    ).all()
    snapshots = list(
        (
            await db.execute(
                select(ScoreSnapshot)
                .where(ScoreSnapshot.client_id == client_id)
                .order_by(ScoreSnapshot.calculated_at.desc(), ScoreSnapshot.id.desc())
            )
        ).scalars()
    )
    scores, score_history = score_projection(snapshots, rows)
    details = await report_details(db, [r for _, _, r in rows], snapshots)
    editable = {
        r.id
        for b, i, r in rows
        if r
        and i.id == instructor_id
        and (
            (r.edited_until and utc_now() < as_utc(r.edited_until))
            or await has_booking_grant(db, b)
        )
    }
    completed = [b for b, _, _ in rows if b.status == "completed"]
    flags = list(
        (
            await db.execute(
                select(AttentionFlag)
                .where(AttentionFlag.client_id == client_id)
                .order_by(AttentionFlag.active.desc(), AttentionFlag.opened_at.desc())
            )
        ).scalars()
    )
    conclusions = list(
        (
            await db.execute(
                select(FinalConclusion)
                .where(FinalConclusion.client_id == client_id)
                .order_by(FinalConclusion.version.desc())
            )
        ).scalars()
    )
    history = [
        {
            "booking_id": b.id,
            "date": b.date.isoformat(),
            "start_at": b.start_at.strftime("%H:%M"),
            "end_at": b.end_at.strftime("%H:%M"),
            "status": b.status,
            "context": b.context,
            "instructor": i.full_name,
            "report_id": r.id if r else None,
            "duration_minutes": b.duration_minutes,
            **(
                details[r.id]
                if r
                else {"skills": [], "exercises": [], "interventions": []}
            ),
            "overall_grade": r.overall_grade_1_5 if r else None,
            "autonomy_level": r.autonomy_level if r else None,
            "quick_verdict": r.quick_verdict if r else None,
            "comment_internal": r.comment_internal if r else None,
            "critical": any(x.is_critical for x in r.interventions) if r else False,
            "can_edit": bool(r and r.id in editable),
            "instructor_id": i.id,
        }
        for b, i, r in rows
    ]
    return {
        "timezone": settings.TIMEZONE,
        "server_now": utc_iso(utc_now()),
        "client": {
            "id": client.id,
            "full_name": client.full_name,
            "phone": client.phone,
            **({"notes_internal": client.notes_internal} if admin else {}),
        },
        "stats": {
            "total_lessons": len(completed),
            "total_hours": round(sum(b.duration_minutes for b in completed) / 60, 1),
            "ground_lessons": sum(b.context == "Учебная площадка" for b in completed),
            "city_lessons": sum(b.context == "Город" for b in completed),
            "no_show": sum(b.status == "no_show" for b, _, _ in rows),
        },
        "scores": scores,
        "history": history,
        "flags": [flag_payload(f) for f in flags],
        "score_history": score_history,
        "conclusions": [
            {
                "id": c.id,
                "text": c.text,
                "status": c.status,
                "version": c.version,
                "created_at": utc_iso(c.created_at),
                "approved_by_type": c.approved_by_type,
                "approved_by_id": c.approved_by_id,
                "approved_by_name": next(
                    (i.full_name for _, i, _ in rows if i.id == c.approved_by_id), None
                )
                if c.approved_by_type == "instructor"
                else None,
                "ai_draft_id": c.ai_draft_id,
            }
            for c in conclusions
        ],
    }
