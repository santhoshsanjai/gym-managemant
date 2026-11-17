from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.common.database import Base


class AuditLog(Base):
    """Trail of important Admin actions (scope section 10, Security)."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(64))
    entity: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


def record(db: Session, actor_id: int | None, action: str, entity: str, entity_id: Any = None, **details: Any) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor_id,
            action=action,
            entity=entity,
            entity_id=None if entity_id is None else str(entity_id),
            details={k: _jsonable(v) for k, v in details.items()} or None,
        )
    )


def _jsonable(v: Any) -> Any:
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    return str(v)
