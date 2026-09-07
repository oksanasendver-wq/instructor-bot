"""Administrator scheduling with conflict detection and audited changes."""

from datetime import date, time, datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from pydantic import BaseModel, Field, model_validator
from app.core.database import get_db
from app.core.time import school_now
from app.models import Booking, Client, Instructor, LessonReport, AttentionFlag
from app.models.booking import Context, TransmissionType, PaymentType
from app.api.admin.dependencies import get_current_admin
from app.services.audit import audit_log
from app.services.lifecycle import reconcile

router = APIRouter()


class BookingCreateRequest(BaseModel):
    client_id: int = Field(gt=0)
    instructor_id: int = Field(gt=0)
    date: date
    start_at: time
    duration_minutes: int = Field(default=60, ge=15, le=240)
    context: Context
    transmission: TransmissionType
    vehicle_id: int | None = None
    payment_type: PaymentType = PaymentType.ALREADY_PAID
    amount_due: Decimal = Field(default=0, ge=0, le=99999999)
    admin_comment: str | None = Field(default=None, max_length=3000)

    @model_validator(mode="after")
    def valid_end(self):
        if (
            self.start_at.tzinfo is not None
            or self.start_at.second
            or self.start_at.microsecond
        ):
            raise ValueError("Укажите местное время школы в формате ЧЧ:ММ")
        end = datetime.combine(self.date, self.start_at) + timedelta(
            minutes=self.duration_minutes
        )
        if end.date() != self.date:
            raise ValueError("Занятие должно закончиться в тот же день")
        return self


def booking_payload(booking, client, instructor, report=None):
    return {
        "id": booking.id,
        "client": {"id": client.id, "full_name": client.full_name},
        "instructor": {"id": instructor.id, "full_name": instructor.full_name},
        "date": booking.date.isoformat(),
        "start_at": booking.start_at.strftime("%H:%M"),
        "end_at": booking.end_at.strftime("%H:%M"),
        "duration_minutes": booking.duration_minutes,
        "context": booking.context,
        "transmission": booking.transmission,
        "status": booking.status,
        "payment_type": booking.payment_type,
        "amount_due": float(booking.amount_due),
        "payment_status": booking.payment_status,
        "admin_comment": booking.admin_comment,
        "overall_grade": report.overall_grade_1_5 if report else None,
        "report_id": report.id if report else None,
    }


async def validate_booking(db, request, exclude_id=0):
    # Stable lock order serializes conflicting inserts for both instructor and client.
    client = (
        await db.execute(
            select(Client).where(Client.id == request.client_id).with_for_update()
        )
    ).scalar_one_or_none()
    instructor = (
        await db.execute(
            select(Instructor)
            .where(Instructor.id == request.instructor_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not client or client.is_archived or not instructor:
        raise HTTPException(404, "Ученик или инструктор не найден")
    if not instructor.is_active:
        raise HTTPException(422, "Выберите активного инструктора")
    if instructor.transmission and instructor.transmission != request.transmission:
        raise HTTPException(422, "КПП занятия не совпадает с КПП инструктора")
    end = (
        datetime.combine(request.date, request.start_at)
        + timedelta(minutes=request.duration_minutes)
    ).time()
    conflict = (
        await db.execute(
            select(Booking.id)
            .where(
                Booking.id != exclude_id,
                Booking.date == request.date,
                Booking.status != "no_show",
                or_(
                    Booking.instructor_id == request.instructor_id,
                    Booking.client_id == request.client_id,
                ),
                Booking.start_at < end,
                Booking.end_at > request.start_at,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if conflict:
        raise HTTPException(409, "Это время уже занято у инструктора или ученика")
    return client, instructor, end


@router.post("/bookings")
async def create_booking(
    request: BookingCreateRequest,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    client, instructor, end = await validate_booking(db, request)
    booking = Booking(
        **request.model_dump(),
        end_at=end,
        status="planned",
        payment_status="pending" if request.amount_due > 0 else "not_required",
    )
    db.add(booking)
    await db.flush()
    await audit_log(
        db,
        "admin",
        0,
        "booking",
        booking.id,
        "create",
        new_values=request.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(booking)
    return {"status": "ok", "booking": booking_payload(booking, client, instructor)}


@router.get("/bookings")
async def list_bookings(
    date_from: date | None = None,
    date_to: date | None = None,
    instructor_id: int | None = None,
    client_id: int | None = None,
    status_filter: str | None = None,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    await reconcile(db)
    query = (
        select(Booking, Client, Instructor, LessonReport)
        .select_from(Booking)
        .join(Client, Booking.client_id == Client.id)
        .join(Instructor, Booking.instructor_id == Instructor.id)
        .outerjoin(LessonReport, LessonReport.booking_id == Booking.id)
    )
    if date_from:
        query = query.where(Booking.date >= date_from)
    if date_to:
        query = query.where(Booking.date <= date_to)
    if instructor_id:
        query = query.where(Booking.instructor_id == instructor_id)
    if client_id:
        query = query.where(Booking.client_id == client_id)
    if status_filter:
        query = query.where(Booking.status == status_filter)
    rows = (
        await db.execute(query.order_by(Booking.date.desc(), Booking.start_at))
    ).all()
    await db.commit()
    return {"total": len(rows), "bookings": [booking_payload(*row) for row in rows]}


@router.patch("/bookings/{booking_id}")
async def update_booking(
    booking_id: int,
    request: BookingCreateRequest,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    booking = (
        await db.execute(
            select(Booking).where(Booking.id == booking_id).with_for_update()
        )
    ).scalar_one_or_none()
    if not booking:
        raise HTTPException(404, "Занятие не найдено")
    if booking.status not in ("planned", "arrival_window"):
        raise HTTPException(
            409, "Начатое занятие нельзя переносить: это изменит историю обучения"
        )
    client, instructor, end = await validate_booking(db, request, booking_id)
    for key, value in request.model_dump().items():
        setattr(booking, key, value)
    booking.end_at = end
    booking.payment_status = "pending" if request.amount_due > 0 else "not_required"
    await audit_log(
        db,
        "admin",
        0,
        "booking",
        booking.id,
        "update",
        new_values=request.model_dump(mode="json"),
    )
    await db.commit()
    return {"status": "ok", "booking": booking_payload(booking, client, instructor)}


@router.delete("/bookings/{booking_id}")
async def delete_booking(
    booking_id: int,
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    booking = (
        await db.execute(
            select(Booking).where(Booking.id == booking_id).with_for_update()
        )
    ).scalar_one_or_none()
    if not booking:
        raise HTTPException(404, "Занятие не найдено")
    if booking.status not in ("planned", "arrival_window", "no_show"):
        raise HTTPException(409, "Нельзя удалить начатое занятие или занятие с отчётом")
    await audit_log(
        db,
        "admin",
        0,
        "booking",
        booking.id,
        "delete",
        old_values={"client_id": booking.client_id, "date": booking.date.isoformat()},
    )
    await db.delete(booking)
    await db.commit()
    return {"status": "ok"}


@router.get("/stats")
async def get_stats(
    admin: dict = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    today = school_now().date()
    await reconcile(db)
    await db.commit()

    async def count(model, *conditions):
        return (
            await db.execute(select(func.count()).select_from(model).where(*conditions))
        ).scalar_one()

    return {
        "today": today.isoformat(),
        "total_bookings_today": await count(Booking, Booking.date == today),
        "completed_today": await count(
            Booking, Booking.date == today, Booking.status == "completed"
        ),
        "in_progress_today": await count(
            Booking, Booking.date == today, Booking.status == "in_progress"
        ),
        "assessment_required": await count(
            Booking,
            Booking.status.in_(["assessment_required", "admin_review_required"]),
        ),
        "no_show_today": await count(
            Booking, Booking.date == today, Booking.status == "no_show"
        ),
        "active_instructors": await count(Instructor, Instructor.is_active.is_(True)),
        "total_clients": await count(Client, Client.is_archived.is_(False)),
        "active_flags": await count(AttentionFlag, AttentionFlag.active.is_(True)),
    }
