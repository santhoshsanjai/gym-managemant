import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database import Base, TimestampMixin
from app.members.models import Member
from app.packages.models import DurationUnit


class SubscriptionStatus(str, enum.Enum):
    """Admin-controlled status. Date-based state is derived (see ``state``)."""

    active = "active"
    suspended = "suspended"
    cancelled = "cancelled"


class SubscriptionState(str, enum.Enum):
    upcoming = "upcoming"
    active = "active"
    expired = "expired"
    suspended = "suspended"
    cancelled = "cancelled"


class Subscription(TimestampMixin, Base):
    """One membership period. Renewals create a new row pointing at the old one
    via ``renewed_from_id``, so history is never overwritten."""

    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint("expiry_date >= start_date", name="dates_ordered"),
        CheckConstraint("amount >= 0", name="amount_non_negative"),
        Index("ix_subscriptions_member_dates", "member_id", "start_date", "expiry_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="RESTRICT"), index=True)
    package_id: Mapped[int] = mapped_column(ForeignKey("packages.id", ondelete="RESTRICT"), index=True)
    # Snapshots so later package edits don't rewrite history.
    package_name: Mapped[str] = mapped_column(String(120))
    duration_value: Mapped[int] = mapped_column(Integer)
    duration_unit: Mapped[DurationUnit] = mapped_column(Enum(DurationUnit, name="duration_unit", create_type=False))
    start_date: Mapped[date] = mapped_column(Date)
    expiry_date: Mapped[date] = mapped_column(Date, index=True)  # last valid day, inclusive
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"),
        default=SubscriptionStatus.active,
        server_default="active",
        index=True,
    )
    renewed_from_id: Mapped[int | None] = mapped_column(ForeignKey("subscriptions.id", ondelete="SET NULL"))
    notes: Mapped[str | None] = mapped_column(Text)

    member: Mapped[Member] = relationship(lazy="joined")

    def state_on(self, day: date) -> SubscriptionState:
        if self.status == SubscriptionStatus.cancelled:
            return SubscriptionState.cancelled
        if self.status == SubscriptionStatus.suspended:
            return SubscriptionState.suspended
        if day < self.start_date:
            return SubscriptionState.upcoming
        if day > self.expiry_date:
            return SubscriptionState.expired
        return SubscriptionState.active
