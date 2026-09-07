from datetime import datetime, date, time
from types import SimpleNamespace
from app.core.time import available_actions


def booking(status="planned"):
    return SimpleNamespace(
        date=date(2026, 9, 6),
        start_at=time(11),
        end_at=time(12),
        duration_minutes=60,
        status=status,
    )


def test_arrival_boundaries():
    assert available_actions(booking(), datetime(2026, 9, 6, 10, 29, 59)) == []
    assert available_actions(booking(), datetime(2026, 9, 6, 10, 30)) == ["arrived"]


def test_no_show_cannot_precede_end():
    assert "no-show" not in available_actions(
        booking(), datetime(2026, 9, 6, 11, 59, 59)
    )
    assert available_actions(booking(), datetime(2026, 9, 6, 12, 0, 1)) == ["no-show"]


def test_finish_requires_attendance_and_planned_end():
    assert (
        available_actions(booking("in_progress"), datetime(2026, 9, 6, 11, 59, 59))
        == []
    )
    assert available_actions(booking("in_progress"), datetime(2026, 9, 6, 12)) == [
        "finish"
    ]


def test_access_expires_at_exact_sixty_minutes():
    assert available_actions(
        booking("assessment_required"), datetime(2026, 9, 6, 12, 59, 59)
    ) == ["report"]
    assert (
        available_actions(booking("assessment_required"), datetime(2026, 9, 6, 13))
        == []
    )


def test_closed_booking_cannot_restart():
    for state in ("completed", "no_show", "admin_review_required"):
        assert available_actions(booking(state), datetime(2026, 9, 6, 11, 30)) == []
