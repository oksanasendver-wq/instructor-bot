from app.core.time import utc_now

"""Reconcile timed states on reads; no separate worker is required."""
from datetime import timedelta
from sqlalchemy import select
from app.models import Booking, AccessGrant
from app.core.time import school_now, booking_window, available_actions
from app.services.audit import audit_log
from app.core.config import settings


async def has_booking_grant(db, booking):
    now = utc_now()
    return (
        await db.execute(
            select(AccessGrant.id)
            .where(
                AccessGrant.booking_id == booking.id,
                AccessGrant.instructor_id == booking.instructor_id,
                AccessGrant.client_id == booking.client_id,
                AccessGrant.valid_from <= now,
                AccessGrant.valid_until > now,
            )
            .limit(1)
        )
    ).scalar_one_or_none() is not None


async def actions_for(db, booking):
    actions = available_actions(booking)
    if (
        not actions
        and booking.status == "assessment_required"
        and await has_booking_grant(db, booking)
    ):
        return ["report"]
    return actions


async def reconcile(db, instructor_id=None):
    now = school_now()
    query = (
        select(Booking)
        .where(
            Booking.status.in_(
                ["planned", "arrival_window", "in_progress", "assessment_required"]
            ),
            Booking.date <= now.date(),
        )
        .with_for_update()
    )
    if instructor_id:
        query = query.where(Booking.instructor_id == instructor_id)
    for booking in (await db.execute(query)).scalars():
        start, end = booking_window(booking)
        if now >= end + timedelta(
            minutes=settings.PROFILE_MINUTES_AFTER
        ) and not await has_booking_grant(db, booking):
            old = booking.status
            booking.status = "admin_review_required"
            await audit_log(
                db,
                "system",
                0,
                "booking",
                booking.id,
                "access_expired",
                old_values={"status": old},
                new_values={"status": booking.status},
            )
        elif booking.status == "planned" and now >= start - timedelta(
            minutes=settings.ARRIVAL_MINUTES_BEFORE
        ):
            booking.status = "arrival_window"
    await db.flush()
