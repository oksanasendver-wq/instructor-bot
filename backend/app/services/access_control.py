from app.core.time import utc_now

"""Instructors retain access to clients whose attendance they recorded."""
from datetime import timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select
from app.models import Booking, AccessGrant
from app.core.config import settings
from app.core.time import school_now, booking_window


class AccessControl:
    def __init__(self, db):
        self.db = db

    async def can_access_client(self, instructor_id, client_id, current_time=None):
        if await self._has_attended_booking(instructor_id, client_id):
            return True
        local_time = current_time or school_now()
        if await self._check_booking_access(instructor_id, client_id, local_time):
            return True
        utc_time = (
            utc_now()
            if current_time is None
            else local_time.replace(tzinfo=ZoneInfo(settings.TIMEZONE))
            .astimezone(ZoneInfo("UTC"))
            .replace(tzinfo=None)
        )
        return await self._check_access_grant(instructor_id, client_id, utc_time)

    async def _has_attended_booking(self, instructor_id, client_id):
        """Attendance is the durable ownership signal for the instructor's directory.

        A scheduled lesson alone remains temporary; a no-show never grants access.
        """
        return (
            await self.db.execute(
                select(Booking.id)
                .where(
                    Booking.instructor_id == instructor_id,
                    Booking.client_id == client_id,
                    Booking.arrived_at.is_not(None),
                )
                .limit(1)
            )
        ).scalar_one_or_none() is not None

    async def _check_booking_access(self, instructor_id, client_id, current_time):
        bookings = (
            (
                await self.db.execute(
                    select(Booking).where(
                        Booking.instructor_id == instructor_id,
                        Booking.client_id == client_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        return any(
            current_time
            < booking_window(b)[1] + timedelta(minutes=settings.PROFILE_MINUTES_AFTER)
            for b in bookings
        )

    async def _check_access_grant(self, instructor_id, client_id, current_time):
        return (
            await self.db.execute(
                select(AccessGrant.id)
                .where(
                    AccessGrant.instructor_id == instructor_id,
                    AccessGrant.client_id == client_id,
                    AccessGrant.valid_from <= current_time,
                    AccessGrant.valid_until > current_time,
                )
                .limit(1)
            )
        ).scalar_one_or_none() is not None
