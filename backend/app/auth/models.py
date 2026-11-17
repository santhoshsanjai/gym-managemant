import enum

from sqlalchemy import Boolean, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base, TimestampMixin


class Role(str, enum.Enum):
    admin = "admin"
    member = "member"


class User(TimestampMixin, Base):
    """Login account. Members have exactly one linked ``Member`` profile."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Login identifier: admin-chosen username, or the member's mobile number.
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # Bumped on password change/reset/deactivation to invalidate issued JWTs.
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
