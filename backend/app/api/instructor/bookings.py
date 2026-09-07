from app.core.time import utc_now, as_utc

"""Instructor schedule and guarded, atomic attendance transitions."""
from datetime import date, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.core.database import get_db
from app.core.config import settings
from app.core.time import school_now, booking_window, available_actions, utc_iso
from app.models import Instructor, Booking, Client, LessonReport, AccessGrant
from app.api.instructor.dependencies import get_current_instructor
from app.services.audit import audit_log
from app.services.lifecycle import reconcile, actions_for, has_booking_grant
from pydantic import BaseModel

router = APIRouter()


def booking_payload(booking, client, report=None):
    _, end = booking_window(booking)
    return {
        "id": booking.id,
        "client": {
            "id": client.id,
            "full_name": client.full_name,
            "phone": client.phone,
        },
        "date": booking.date.isoformat(),
        "start_at": booking.start_at.strftime("%H:%M"),
        "end_at": booking.end_at.strftime("%H:%M"),
        "duration_minutes": booking.duration_minutes,
        "context": booking.context,
        "transmission": booking.transmission,
        "payment_type": booking.payment_type,
        "amount_due": float(booking.amount_due),
        "payment_status": booking.payment_status,
        "status": booking.status,
        "admin_comment": booking.admin_comment,
        "actions": available_actions(booking),
        "access_until": (
            end + timedelta(minutes=settings.PROFILE_MINUTES_AFTER)
        ).isoformat(),
        "report_id": report.id if report else None,
        "overall_grade": report.overall_grade_1_5 if report else None,
        "can_edit_report": bool(
            report and report.edited_until and utc_now() < as_utc(report.edited_until)
        ),
        "edited_until": utc_iso(report.edited_until) if report else None,
    }


@router.get("/me")
async def profile(
    request: Request, current_instructor: Instructor = Depends(get_current_instructor)
):
    return {
        "id": current_instructor.id,
        "full_name": current_instructor.full_name,
        "phone": current_instructor.phone,
        "transmission": current_instructor.transmission,
        "is_active": current_instructor.is_active,
        "timezone": settings.TIMEZONE,
        "today": school_now().date().isoformat(),
        "school_time": school_now()
        .replace(tzinfo=ZoneInfo(settings.TIMEZONE))
        .isoformat(),
        "app_name": request.app.title,
        "app_version": request.app.version,
    }


@router.get("/me/statistics")
async def statistics(
    current_instructor: Instructor = Depends(get_current_instructor),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Booking, LessonReport)
            .outerjoin(LessonReport, LessonReport.booking_id == Booking.id)
            .where(Booking.instructor_id == current_instructor.id)
        )
    ).all()
    completed = [booking for booking, _ in rows if booking.status == "completed"]
    grades = [
        report.overall_grade_1_5
        for booking, report in rows
        if report and booking.status == "completed"
    ]
    return {
        "total_lessons": len(completed),
        "total_hours": round(
            sum(booking.duration_minutes for booking in completed) / 60, 1
        ),
        "total_clients": len(
            {booking.client_id for booking, _ in rows if booking.arrived_at is not None}
        ),
        "ground_lessons": sum(
            booking.context == "Учебная площадка" for booking in completed
        ),
        "city_lessons": sum(booking.context == "Город" for booking in completed),
        "no_show": sum(booking.status == "no_show" for booking, _ in rows),
        "pending_reports": sum(
            report is None
            and booking.status
            in ("completed", "assessment_required", "admin_review_required")
            and booking.arrived_at is not None
            for booking, report in rows
        ),
        "reported_lessons": len(grades),
        "average_grade": round(sum(grades) / len(grades), 2) if grades else None,
    }


@router.get("/bookings/me/today")
@router.get("/bookings")
async def get_instructor_bookings(
    today_only: bool = True,
    on_date: date | None = None,
    history: bool = False,
    current_instructor: Instructor = Depends(get_current_instructor),
    db: AsyncSession = Depends(get_db),
):
    await reconcile(db, current_instructor.id)
    query = (
        select(Booking, Client, LessonReport)
        .select_from(Booking)
        .join(Client, Booking.client_id == Client.id)
        .outerjoin(LessonReport, LessonReport.booking_id == Booking.id)
        .where(Booking.instructor_id == current_instructor.id)
    )
    if history:
        query = (
            query.where(Booking.status == "completed")
            .order_by(Booking.date.desc(), Booking.start_at.desc())
            .limit(100)
        )
    else:
        today = school_now().date()
        condition = (
            Booking.date == (on_date or today)
            if today_only or on_date
            else Booking.date >= today
        )
        if not on_date or on_date == today:
            grants = select(AccessGrant.booking_id).where(
                AccessGrant.instructor_id == current_instructor.id,
                AccessGrant.valid_from <= utc_now(),
                AccessGrant.valid_until > utc_now(),
            )
            condition = or_(condition, Booking.id.in_(grants))
        query = query.where(condition)
        query = query.order_by(Booking.date, Booking.start_at).limit(200)
    rows = (await db.execute(query)).all()
    response = []
    from app.services.access_control import AccessControl

    access = AccessControl(db)
    visible_clients = {}
    for row in rows:
        payload = booking_payload(*row)
        if row[0].client_id not in visible_clients:
            visible_clients[row[0].client_id] = await access.can_access_client(
                current_instructor.id, row[0].client_id
            )
        if row[1].is_archived or (
            not visible_clients[row[0].client_id] and not payload["can_edit_report"]
        ):
            continue
        payload["actions"] = await actions_for(db, row[0])
        if row[2] and await has_booking_grant(db, row[0]):
            payload["can_edit_report"] = True
        response.append(payload)
    await db.commit()
    return response


@router.get("/bookings/{booking_id}")
async def get_booking_detail(
    booking_id: int,
    current_instructor: Instructor = Depends(get_current_instructor),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(Booking, Client, LessonReport)
            .select_from(Booking)
            .join(Client, Booking.client_id == Client.id)
            .outerjoin(LessonReport, LessonReport.booking_id == Booking.id)
            .where(Booking.id == booking_id)
        )
    ).first()
    if not row:
        raise HTTPException(404, "Занятие не найдено")
    from app.services.access_control import AccessControl

    owned = row[0].instructor_id == current_instructor.id
    accessible = await AccessControl(db).can_access_client(
        current_instructor.id, row[0].client_id
    )
    if not owned and not accessible:
        raise HTTPException(404, "Занятие не найдено")
    payload = booking_payload(*row)
    instructor = await db.get(Instructor, row[0].instructor_id)
    payload["instructor"] = {
        "id": instructor.id,
        "full_name": instructor.full_name,
        "phone": instructor.phone,
    }
    payload["actions"] = await actions_for(db, row[0]) if owned else []
    payload["can_edit_report"] = owned and payload["can_edit_report"]
    if owned and row[2] and await has_booking_grant(db, row[0]):
        payload["can_edit_report"] = True
    if not payload["can_edit_report"] and not accessible:
        raise HTTPException(403, "Время доступа к занятию истекло")
    return payload


async def transition(booking_id, action, instructor, db):
    booking = (
        await db.execute(
            select(Booking)
            .where(Booking.id == booking_id, Booking.instructor_id == instructor.id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not booking:
        raise HTTPException(404, "Занятие не найдено")
    if action not in available_actions(booking):
        raise HTTPException(
            409,
            "Действие недоступно для текущего статуса или времени занятия. Обновите расписание",
        )
    old = booking.status
    booking.status = {
        "arrived": "in_progress",
        "no-show": "no_show",
        "finish": "assessment_required",
    }[action]
    if action == "arrived":
        booking.arrived_at = utc_now()
    if action == "finish":
        booking.finished_at = utc_now()
    await audit_log(
        db,
        "instructor",
        instructor.id,
        "booking",
        booking.id,
        action,
        old_values={"status": old},
        new_values={"status": booking.status},
    )
    await db.commit()
    return {"status": "ok", "booking_status": booking.status}


@router.post("/bookings/{booking_id}/arrived")
async def mark_arrived(
    booking_id: int,
    current_instructor: Instructor = Depends(get_current_instructor),
    db: AsyncSession = Depends(get_db),
):
    return await transition(booking_id, "arrived", current_instructor, db)


@router.post("/bookings/{booking_id}/no-show")
async def mark_no_show(
    booking_id: int,
    current_instructor: Instructor = Depends(get_current_instructor),
    db: AsyncSession = Depends(get_db),
):
    return await transition(booking_id, "no-show", current_instructor, db)


@router.post("/bookings/{booking_id}/finish")
async def finish_lesson(
    booking_id: int,
    current_instructor: Instructor = Depends(get_current_instructor),
    db: AsyncSession = Depends(get_db),
):
    return await transition(booking_id, "finish", current_instructor, db)


class PaymentInput(BaseModel):
    received: bool


@router.post("/bookings/{booking_id}/payment")
async def payment(
    booking_id: int,
    request: PaymentInput,
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
    from app.services.access_control import AccessControl

    if not await AccessControl(db).can_access_client(
        current_instructor.id, booking.client_id
    ):
        raise HTTPException(403, "Время доступа истекло")
    if booking.amount_due <= 0 or booking.status not in (
        "in_progress",
        "assessment_required",
        "completed",
    ):
        raise HTTPException(409, "Подтверждение оплаты недоступно")
    old = booking.payment_status
    booking.payment_status = "received" if request.received else "pending"
    await audit_log(
        db,
        "instructor",
        current_instructor.id,
        "booking",
        booking.id,
        "payment",
        old_values={"payment_status": old},
        new_values={"payment_status": booking.payment_status},
    )
    await db.commit()
    return {"status": "ok", "payment_status": booking.payment_status}
