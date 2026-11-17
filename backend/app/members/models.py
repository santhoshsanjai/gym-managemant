import enum
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database import Base, TimestampMixin
from app.trainers.models import Trainer


class MemberStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"


class Member(TimestampMixin, Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), unique=True)
    full_name: Mapped[str] = mapped_column(String(150), index=True)
    mobile: Mapped[str] = mapped_column(String(20), unique=True)
    email: Mapped[str | None] = mapped_column(String(255))
    gender: Mapped[Gender | None] = mapped_column(Enum(Gender, name="gender"))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    address: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(String(500))
    joining_date: Mapped[date] = mapped_column(Date, index=True)
    trainer_id: Mapped[int | None] = mapped_column(ForeignKey("trainers.id", ondelete="SET NULL"), index=True)
    status: Mapped[MemberStatus] = mapped_column(
        Enum(MemberStatus, name="member_status"), default=MemberStatus.active, server_default="active", index=True
    )

    trainer: Mapped[Trainer | None] = relationship(lazy="joined")

    @property
    def member_code(self) -> str:
        return f"GYM{self.id:05d}"
