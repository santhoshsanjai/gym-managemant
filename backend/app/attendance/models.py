import enum
from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database import Base
from app.members.models import Member


class AttendanceSource(str, enum.Enum):
    qr = "qr"
    manual = "manual"  # entered by Admin


class QrToken(Base):
    """Short-lived token shown as the gym's rotating QR code."""

    __tablename__ = "qr_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    issued_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (Index("ix_attendance_member_date", "member_id", "attendance_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="RESTRICT"))
    attendance_date: Mapped[date] = mapped_column(Date, index=True)  # gym business day
    checked_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # server time, UTC
    source: Mapped[AttendanceSource] = mapped_column(Enum(AttendanceSource, name="attendance_source"))
    qr_token_id: Mapped[int | None] = mapped_column(ForeignKey("qr_tokens.id", ondelete="SET NULL"))
    recorded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    member: Mapped[Member] = relationship(lazy="joined")
