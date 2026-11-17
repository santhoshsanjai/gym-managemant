"""Subscription reminder generation and delivery.

Runs from the background scheduler (daily, gym-local time) and can also be
triggered manually by an Admin. Every notification carries a ``dedupe_key``
so re-running the job (or running it from several workers) is harmless.
"""

import json
import logging
from datetime import date, timedelta

from sqlalchemy import and_, exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, aliased

from app.auth.models import Role, User
from app.common.config import get_settings
from app.common.timeutil import now_utc, today
from app.members.models import Member, MemberStatus
from app.notifications.models import Notification, NotificationType, PushSubscription
from app.subscriptions.models import Subscription, SubscriptionStatus

log = logging.getLogger(__name__)

# How many days back the "expired" notice is still sent, so a missed run
# (server down for a day) is caught up the next time the job runs.
EXPIRED_CATCH_UP_DAYS = 3


def _not_renewed():
    """No later active subscription continues right after this one."""
    nxt = aliased(Subscription)
    return ~exists(
        select(nxt.id).where(
            nxt.member_id == Subscription.member_id,
            nxt.id != Subscription.id,
            nxt.status == SubscriptionStatus.active,
            nxt.start_date <= Subscription.expiry_date + 1,
            nxt.expiry_date > Subscription.expiry_date,
        )
    )


def _due_subscriptions(db: Session, cond):
    return db.execute(
        select(Subscription, Member.user_id)
        .join(Member, Member.id == Subscription.member_id)
        .join(User, User.id == Member.user_id)
        .where(
            Subscription.status == SubscriptionStatus.active,
            Member.status == MemberStatus.active,
            User.is_active.is_(True),
            cond,
            _not_renewed(),
        )
    ).all()


def _insert(db: Session, **values) -> int | None:
    stmt = insert(Notification).values(**values).on_conflict_do_nothing(index_elements=["dedupe_key"])
    return db.execute(stmt.returning(Notification.id)).scalar()


def _fmt(d: date) -> str:
    return d.strftime("%d %b %Y")


def generate_reminders(db: Session, day: date | None = None) -> list[int]:
    s = get_settings()
    day = day or today()
    created: list[int] = []

    for n in s.reminder_days_before_expiry:
        for sub, user_id in _due_subscriptions(db, Subscription.expiry_date == day + timedelta(days=n)):
            when = "today" if n == 0 else ("tomorrow" if n == 1 else f"in {n} days")
            nid = _insert(
                db,
                user_id=user_id,
                type=NotificationType.expiry_reminder,
                title=f"Your membership expires {when}",
                body=f"Your {sub.package_name} membership is valid until {_fmt(sub.expiry_date)}. "
                "Please renew at the front desk to keep your access.",
                subscription_id=sub.id,
                dedupe_key=f"reminder:{sub.id}:{n}",
            )
            if nid:
                created.append(nid)

    expired_cond = and_(
        Subscription.expiry_date < day, Subscription.expiry_date >= day - timedelta(days=EXPIRED_CATCH_UP_DAYS)
    )
    for sub, user_id in _due_subscriptions(db, expired_cond):
        nid = _insert(
            db,
            user_id=user_id,
            type=NotificationType.expired,
            title="Your membership has expired",
            body=f"Your {sub.package_name} membership ended on {_fmt(sub.expiry_date)}. "
            "Renew at the front desk to continue using the gym.",
            subscription_id=sub.id,
            dedupe_key=f"expired:{sub.id}",
        )
        if nid:
            created.append(nid)

    created += _admin_digest(db, day)
    db.commit()
    deliver_push(db, created)
    return created


def _admin_digest(db: Session, day: date) -> list[int]:
    s = get_settings()
    window = day + timedelta(days=s.upcoming_expiry_window_days)
    upcoming = len(_due_subscriptions(db, and_(Subscription.expiry_date >= day, Subscription.expiry_date <= window)))
    expired = len(_due_subscriptions(db, Subscription.expiry_date == day - timedelta(days=1)))
    if not (upcoming or expired):
        return []
    parts = []
    if upcoming:
        parts.append(f"{upcoming} membership(s) expire within {s.upcoming_expiry_window_days} days")
    if expired:
        parts.append(f"{expired} membership(s) expired yesterday")
    ids = []
    for admin_id in db.scalars(select(User.id).where(User.role == Role.admin, User.is_active.is_(True))):
        nid = _insert(
            db,
            user_id=admin_id,
            type=NotificationType.general,
            title="Membership expiry alert",
            body="; ".join(parts) + ".",
            dedupe_key=f"admin-digest:{day.isoformat()}:{admin_id}",
        )
        if nid:
            ids.append(nid)
    return ids


def deliver_push(db: Session, notification_ids: list[int]) -> int:
    """Best-effort Web Push for new notifications. In-app copies always exist."""
    s = get_settings()
    if not (notification_ids and s.vapid_private_key and s.vapid_public_key):
        return 0
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:  # pragma: no cover
        log.warning("pywebpush not installed; skipping push delivery")
        return 0
    sent = 0
    notes = db.scalars(select(Notification).where(Notification.id.in_(notification_ids))).all()
    for note in notes:
        subs = db.scalars(select(PushSubscription).where(PushSubscription.user_id == note.user_id)).all()
        payload = json.dumps({"notification": {"title": note.title, "body": note.body, "data": {"url": "/"}}})
        for ps in subs:
            try:
                webpush(
                    subscription_info={"endpoint": ps.endpoint, "keys": {"p256dh": ps.p256dh, "auth": ps.auth}},
                    data=payload,
                    vapid_private_key=s.vapid_private_key,
                    vapid_claims={"sub": s.vapid_subject},
                )
                note.push_sent_at = now_utc()
                sent += 1
            except WebPushException as e:  # pragma: no cover - network
                status = getattr(e.response, "status_code", None)
                if status in (404, 410):
                    db.delete(ps)
                else:
                    log.warning("Push to %s failed: %s", ps.endpoint[:40], e)
    db.commit()
    return sent
