import enum

from sqlalchemy import Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base, TimestampMixin


class TrainerStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class Trainer(TimestampMixin, Base):
    __tablename__ = "trainers"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150), index=True)
    mobile: Mapped[str] = mapped_column(String(20), unique=True)
    email: Mapped[str | None] = mapped_column(String(255))
    specialization: Mapped[str | None] = mapped_column(String(150))
    experience_years: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TrainerStatus] = mapped_column(
        Enum(TrainerStatus, name="trainer_status"), default=TrainerStatus.active, server_default="active", index=True
    )

    @property
    def trainer_code(self) -> str:
        return f"TR{self.id:04d}"
