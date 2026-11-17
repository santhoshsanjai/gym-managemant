import calendar
import enum
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Enum, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base, TimestampMixin


class DurationUnit(str, enum.Enum):
    days = "days"
    months = "months"


def add_duration(start: date, value: int, unit: DurationUnit) -> date:
    """Last valid day (inclusive) of a membership starting on ``start``.

    1 month from 2025-01-31 ends on 2025-02-27 (the day before 2025-02-28),
    i.e. calendar months clamp to the end of shorter months.
    """
    if unit == DurationUnit.days:
        return start + timedelta(days=value - 1)
    month_index = start.month - 1 + value
    year, month = start.year + month_index // 12, month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day) - timedelta(days=1)


class Package(TimestampMixin, Base):
    __tablename__ = "packages"
    __table_args__ = (
        CheckConstraint("duration_value > 0", name="duration_positive"),
        CheckConstraint("price >= 0", name="price_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    duration_value: Mapped[int] = mapped_column(Integer)
    duration_unit: Mapped[DurationUnit] = mapped_column(Enum(DurationUnit, name="duration_unit"))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", index=True)
