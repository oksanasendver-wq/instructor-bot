"""Booking dates are school-local; stored audit/report timestamps are UTC."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.config import settings


def school_now() -> datetime:
    return datetime.now(ZoneInfo(settings.TIMEZONE)).replace(tzinfo=None)


def utc_iso(value):
    return as_utc(value).isoformat() if value else None


def utc_now():
    return datetime.now(timezone.utc)


def as_utc(value):
    """SQLite loses offsets; PostgreSQL returns aware timestamps."""
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def booking_window(booking):
    start = datetime.combine(booking.date, booking.start_at)
    return start, start + timedelta(minutes=booking.duration_minutes)


def available_actions(booking, now=None):
    now = now or school_now()
    start, end = booking_window(booking)
    if now >= end + timedelta(minutes=settings.PROFILE_MINUTES_AFTER):
        return []
    if booking.status in ("planned", "arrival_window"):
        if start - timedelta(minutes=settings.ARRIVAL_MINUTES_BEFORE) <= now <= end:
            return ["arrived"]
        if now >= end:
            return ["no-show"]
    if booking.status == "in_progress" and now >= end:
        return ["finish"]
    if booking.status == "assessment_required":
        return ["report"]
    return []
