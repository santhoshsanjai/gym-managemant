from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select, update

from app.auth.deps import DB, AdminUser, CurrentUser
from app.common import audit
from app.common.config import get_settings
from app.common.errors import not_found
from app.common.pagination import Page, PageParams, paginate
from app.common.timeutil import now_utc
from app.notifications import service
from app.notifications.models import Notification, PushSubscription
from app.notifications.schemas import NotificationOut, PushSubscriptionIn, ReminderRunResult

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=Page[NotificationOut])
def my_notifications(db: DB, user: CurrentUser, params: PageParams = Depends(), unread_only: bool = False):
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    return paginate(db, stmt.order_by(Notification.created_at.desc(), Notification.id.desc()), params)


class UnreadCount(BaseModel):
    unread: int


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(db: DB, user: CurrentUser):
    n = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
    )
    return UnreadCount(unread=n)


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, db: DB, user: CurrentUser):
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != user.id:
        raise not_found("Notification")
    if n.read_at is None:
        n.read_at = now_utc()
        db.commit()
    return n


@router.post("/read-all", status_code=204)
def mark_all_read(db: DB, user: CurrentUser):
    db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=now_utc())
    )
    db.commit()


class PublicKey(BaseModel):
    public_key: str | None
    enabled: bool


@router.get("/push/public-key", response_model=PublicKey)
def push_public_key(_: CurrentUser):
    key = get_settings().vapid_public_key
    return PublicKey(public_key=key, enabled=bool(key and get_settings().vapid_private_key))


@router.post("/push/subscribe", status_code=204)
def push_subscribe(body: PushSubscriptionIn, db: DB, user: CurrentUser):
    ps = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
    if ps is None:
        ps = PushSubscription(endpoint=body.endpoint, user_id=user.id, p256dh=body.keys.p256dh, auth=body.keys.auth)
        db.add(ps)
    else:  # endpoint re-registered (possibly by another user on a shared device)
        ps.user_id, ps.p256dh, ps.auth = user.id, body.keys.p256dh, body.keys.auth
    db.commit()


@router.post("/push/unsubscribe", status_code=204)
def push_unsubscribe(body: PushSubscriptionIn, db: DB, user: CurrentUser):
    ps = db.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint, PushSubscription.user_id == user.id)
    )
    if ps:
        db.delete(ps)
        db.commit()


@router.post("/run-reminders", response_model=ReminderRunResult)
def run_reminders(db: DB, admin: AdminUser):
    """Manually run the reminder job (it also runs daily on a schedule)."""
    ids = service.generate_reminders(db)
    audit.record(db, admin.id, "run_reminders", "notification", None, created=len(ids))
    db.commit()
    return ReminderRunResult(created=len(ids))
