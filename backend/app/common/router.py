from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from app.auth.deps import DB, CurrentUser, require_admin
from app.auth.models import User
from app.common.audit import AuditLog
from app.common.config import get_settings
from app.common.pagination import Page, PageParams, paginate
from app.common.timeutil import now_utc, today

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    return {"status": "ok"}


class Policy(BaseModel):
    gym_name: str
    timezone: str
    gym_day_start_hour: int
    today: date
    server_time: str
    attendance_max_checkins_per_day: int
    attendance_require_active_subscription: bool
    qr_token_ttl_seconds: int
    reminder_days_before_expiry: list[int]
    member_editable_fields: list[str]


@router.get("/settings/policy", response_model=Policy)
def policy(_: CurrentUser):
    """Effective business rules, so the UI can explain them to users."""
    s = get_settings()
    return Policy(
        gym_name=s.app_name,
        timezone=s.gym_timezone,
        gym_day_start_hour=s.gym_day_start_hour,
        today=today(),
        server_time=now_utc().isoformat(),
        attendance_max_checkins_per_day=s.attendance_max_checkins_per_day,
        attendance_require_active_subscription=s.attendance_require_active_subscription,
        qr_token_ttl_seconds=s.qr_token_ttl_seconds,
        reminder_days_before_expiry=s.reminder_days_before_expiry,
        member_editable_fields=s.member_editable_fields,
    )


class AuditOut(BaseModel):
    id: int
    actor_user_id: int | None
    actor_username: str | None = None
    action: str
    entity: str
    entity_id: str | None
    details: dict | None
    created_at: str

    @classmethod
    def from_row(cls, r: AuditLog, actor: str | None = None) -> "AuditOut":
        return cls(
            **{k: getattr(r, k) for k in ("id", "actor_user_id", "action", "entity", "entity_id", "details")},
            actor_username=actor,
            created_at=r.created_at.isoformat(),
        )


@router.get("/audit-logs", response_model=Page[AuditOut], dependencies=[Depends(require_admin)])
def audit_logs(
    db: DB,
    params: PageParams = Depends(),
    entity: str | None = None,
    action: str | None = None,
    entity_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    stmt = select(AuditLog)
    if entity:
        stmt = stmt.where(AuditLog.entity == entity)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    tz = get_settings().tz
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= datetime.combine(date_from, time.min, tz))
    if date_to:
        stmt = stmt.where(AuditLog.created_at < datetime.combine(date_to + timedelta(days=1), time.min, tz))
    page = paginate(db, stmt.order_by(AuditLog.id.desc()), params)
    ids = {r.actor_user_id for r in page["items"] if r.actor_user_id}
    names = dict(db.execute(select(User.id, User.username).where(User.id.in_(ids))).all()) if ids else {}
    page["items"] = [AuditOut.from_row(r, names.get(r.actor_user_id)) for r in page["items"]]
    return page
