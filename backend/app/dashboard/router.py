from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.attendance.models import Attendance
from app.attendance.schemas import AttendanceOut
from app.auth.deps import DB, AdminUser, CurrentMember
from app.common.config import get_settings
from app.common.timeutil import month_bounds, today
from app.members.models import Member, MemberStatus
from app.members.schemas import MemberOut
from app.notifications.models import Notification
from app.notifications.schemas import NotificationOut
from app.payments.models import Payment, PaymentStatus
from app.subscriptions import service as sub_service
from app.subscriptions.models import Subscription, SubscriptionStatus
from app.subscriptions.queries import has_active_subscription, has_expired_membership
from app.subscriptions.schemas import SubscriptionOut
from app.trainers.models import Trainer, TrainerStatus

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class AdminDashboard(BaseModel):
    as_of: date
    year: int
    month: int
    total_members: int
    active_members: int
    expired_members: int
    inactive_accounts: int
    todays_attendance: int
    total_trainers: int
    monthly_revenue: Decimal
    new_members_this_month: int
    upcoming_expiries: list[SubscriptionOut]
    recently_expired: list[SubscriptionOut]


@router.get("/admin", response_model=AdminDashboard)
def admin_dashboard(
    db: DB,
    _: AdminUser,
    year: int | None = Query(None, ge=2000, le=2100),
    month: int | None = Query(None, ge=1, le=12),
):
    """Definitions:
    * active members: account active and a subscription covers today
    * expired members: had a subscription before but none covers today
    * monthly revenue: sum of payments with status ``paid`` by payment date
    """
    s = get_settings()
    day = today()
    year, month = year or day.year, month or day.month
    start, end = month_bounds(year, month)
    count = lambda stmt: db.scalar(select(func.count()).select_from(Member).where(*stmt)) or 0  # noqa: E731

    window_end = day + timedelta(days=s.upcoming_expiry_window_days)
    active_sub = Subscription.status == SubscriptionStatus.active
    upcoming = db.scalars(
        select(Subscription)
        .where(active_sub, Subscription.start_date <= day, Subscription.expiry_date.between(day, window_end))
        .order_by(Subscription.expiry_date)
        .limit(50)
    ).all()
    expired = db.scalars(
        select(Subscription)
        .where(active_sub, Subscription.expiry_date.between(day - timedelta(days=30), day - timedelta(days=1)))
        .order_by(Subscription.expiry_date.desc())
        .limit(50)
    ).all()
    # Hide expiries that were already renewed.
    renewed = lambda sub: db.scalar(  # noqa: E731
        select(Subscription.id)
        .where(
            Subscription.member_id == sub.member_id,
            Subscription.id != sub.id,
            active_sub,
            Subscription.expiry_date > sub.expiry_date,
        )
        .limit(1)
    )
    upcoming = [x for x in upcoming if not renewed(x)]
    expired = [x for x in expired if not renewed(x)]

    return AdminDashboard(
        as_of=day,
        year=year,
        month=month,
        total_members=count([]),
        active_members=count([Member.status == MemberStatus.active, has_active_subscription(day)]),
        expired_members=count([has_expired_membership(day)]),
        inactive_accounts=count([Member.status == MemberStatus.inactive]),
        todays_attendance=db.scalar(
            select(func.count()).select_from(Attendance).where(Attendance.attendance_date == day)
        ),
        total_trainers=db.scalar(
            select(func.count()).select_from(Trainer).where(Trainer.status == TrainerStatus.active)
        ),
        monthly_revenue=db.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.status == PaymentStatus.paid, Payment.payment_date >= start, Payment.payment_date < end
            )
        ),
        new_members_this_month=count([Member.joining_date >= start, Member.joining_date < end]),
        upcoming_expiries=sub_service.to_out(db, upcoming, day),
        recently_expired=sub_service.to_out(db, expired, day),
    )


class MemberDashboard(BaseModel):
    as_of: date
    profile: MemberOut
    current_subscription: SubscriptionOut | None
    upcoming_subscription: SubscriptionOut | None
    latest_subscription: SubscriptionOut | None
    remaining_days: int
    checked_in_today: bool
    todays_checkin: AttendanceOut | None
    total_attendance: int
    attendance_this_month: int
    recent_notifications: list[NotificationOut]
    unread_notifications: int


@router.get("/member", response_model=MemberDashboard)
def member_dashboard(db: DB, member: CurrentMember):
    day = today()
    current, upcoming = sub_service.current_and_upcoming(db, member.id, day)
    latest = sub_service.latest(db, member.id)
    out = lambda s: sub_service.to_out(db, [s], day)[0] if s else None  # noqa: E731
    cur_out = out(current)
    todays = db.scalar(
        select(Attendance)
        .where(Attendance.member_id == member.id, Attendance.attendance_date == day)
        .order_by(Attendance.checked_in_at)
        .limit(1)
    )
    start, end = month_bounds(day.year, day.month)
    att_count = lambda *c: db.scalar(  # noqa: E731
        select(func.count()).select_from(Attendance).where(Attendance.member_id == member.id, *c)
    )
    notes = db.scalars(
        select(Notification)
        .where(Notification.user_id == member.user_id)
        .order_by(Notification.created_at.desc())
        .limit(5)
    ).all()
    unread = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == member.user_id, Notification.read_at.is_(None))
    )
    return MemberDashboard(
        as_of=day,
        profile=member,
        current_subscription=cur_out,
        upcoming_subscription=out(upcoming),
        latest_subscription=out(latest),
        remaining_days=cur_out.remaining_days if cur_out else 0,
        checked_in_today=todays is not None,
        todays_checkin=todays,
        total_attendance=att_count(),
        attendance_this_month=att_count(Attendance.attendance_date >= start, Attendance.attendance_date < end),
        recent_notifications=notes,
        unread_notifications=unread,
    )
