"""Reusable SQL fragments for date-based membership state."""

from datetime import date

from sqlalchemy import and_, exists, select

from app.members.models import Member
from app.subscriptions.models import Subscription, SubscriptionStatus


def covers(day: date):
    return and_(
        Subscription.status == SubscriptionStatus.active,
        Subscription.start_date <= day,
        Subscription.expiry_date >= day,
    )


def has_active_subscription(day: date):
    return exists(select(Subscription.id).where(Subscription.member_id == Member.id, covers(day)))


def has_any_subscription():
    return exists(
        select(Subscription.id).where(
            Subscription.member_id == Member.id, Subscription.status != SubscriptionStatus.cancelled
        )
    )


def has_expired_membership(day: date):
    """Had a (non-cancelled) subscription before, but nothing covers today."""
    return and_(has_any_subscription(), ~has_active_subscription(day))
