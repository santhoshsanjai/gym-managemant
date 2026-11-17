"""Time helpers. All persisted timestamps are UTC; the gym day is derived from
server time in the configured gym time zone (never from the client device)."""

from datetime import date, datetime, timedelta, timezone

from app.common.config import get_settings

# Tests may freeze the clock by setting this (see tests/conftest.py).
frozen_now: datetime | None = None


def now_utc() -> datetime:
    return frozen_now or datetime.now(timezone.utc)


def gym_day(at: datetime | None = None) -> date:
    """The gym business day that a UTC instant belongs to."""
    s = get_settings()
    at = at or now_utc()
    local = at.astimezone(s.tz)
    return (local - timedelta(hours=s.gym_day_start_hour)).date()


def today() -> date:
    return gym_day()


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """First day of the month and first day of the next month."""
    start = date(year, month, 1)
    end = date(year + (month == 12), (month % 12) + 1, 1)
    return start, end
