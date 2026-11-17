from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.common import audit
from app.common.errors import bad_request, conflict, not_found
from app.common.timeutil import today
from app.members.models import Member, MemberStatus
from app.packages.models import Package, add_duration
from app.payments.models import Payment, PaymentStatus
from app.subscriptions.models import Subscription, SubscriptionState, SubscriptionStatus
from app.subscriptions.schemas import InlinePayment, SubscriptionOut


def get_subscription(db: Session, sub_id: int) -> Subscription:
    s = db.get(Subscription, sub_id)
    if s is None:
        raise not_found("Subscription")
    return s


def _check_overlap(db: Session, member_id: int, start: date, end: date, exclude_id: int | None = None) -> None:
    q = select(Subscription.id).where(
        Subscription.member_id == member_id,
        Subscription.status == SubscriptionStatus.active,
        Subscription.start_date <= end,
        Subscription.expiry_date >= start,
    )
    if exclude_id:
        q = q.where(Subscription.id != exclude_id)
    if db.scalar(q.limit(1)):
        raise conflict("This period overlaps another active subscription for the member. Use renew instead.")


def _create(
    db: Session,
    member: Member,
    package: Package,
    start: date,
    amount: Decimal | None,
    notes: str | None,
    payment: InlinePayment | None,
    actor: User,
    renewed_from: Subscription | None = None,
) -> Subscription:
    if member.status != MemberStatus.active:
        raise bad_request("Member account is inactive")
    if not package.is_active:
        raise bad_request("Package is inactive and cannot be assigned")
    end = add_duration(start, package.duration_value, package.duration_unit)
    _check_overlap(db, member.id, start, end)
    sub = Subscription(
        member_id=member.id,
        package_id=package.id,
        package_name=package.name,
        duration_value=package.duration_value,
        duration_unit=package.duration_unit,
        start_date=start,
        expiry_date=end,
        amount=package.price if amount is None else amount,
        notes=notes,
        renewed_from_id=renewed_from.id if renewed_from else None,
    )
    db.add(sub)
    db.flush()
    if payment:
        db.add(
            Payment(
                member_id=member.id,
                subscription_id=sub.id,
                amount=payment.amount or sub.amount,
                payment_date=payment.payment_date or today(),
                method=payment.method,
                reference=payment.reference,
                status=payment.status,
                notes=payment.notes,
                recorded_by_id=actor.id,
            )
        )
    audit.record(
        db,
        actor.id,
        "renew" if renewed_from else "create",
        "subscription",
        sub.id,
        member_id=member.id,
        package=package.name,
        start=start,
        expiry=end,
    )
    db.commit()
    db.refresh(sub)
    return sub


def create_subscription(db: Session, data, actor: User) -> Subscription:
    member = db.get(Member, data.member_id)
    if member is None:
        raise not_found("Member")
    package = db.get(Package, data.package_id)
    if package is None:
        raise not_found("Package")
    return _create(db, member, package, data.start_date or today(), data.amount, data.notes, data.payment, actor)


def renew_subscription(db: Session, prev: Subscription, data, actor: User) -> Subscription:
    if prev.status == SubscriptionStatus.cancelled:
        raise bad_request("A cancelled subscription cannot be renewed; create a new one instead")
    package = db.get(Package, data.package_id or prev.package_id)
    if package is None:
        raise not_found("Package")
    # Default: continue the day after the latest active period ends, or today if lapsed.
    latest_end = db.scalar(
        select(func.max(Subscription.expiry_date)).where(
            Subscription.member_id == prev.member_id, Subscription.status == SubscriptionStatus.active
        )
    )
    default_start = max(today(), (latest_end or prev.expiry_date) + timedelta(days=1))
    start = data.start_date or default_start
    return _create(db, prev.member, package, start, data.amount, data.notes, data.payment, actor, renewed_from=prev)


def list_query(
    member_id: int | None,
    state: SubscriptionState | None,
    package_id: int | None,
    expiring_within_days: int | None,
    day: date,
):
    stmt = select(Subscription)
    if member_id:
        stmt = stmt.where(Subscription.member_id == member_id)
    if package_id:
        stmt = stmt.where(Subscription.package_id == package_id)
    active = Subscription.status == SubscriptionStatus.active
    if state == SubscriptionState.active:
        stmt = stmt.where(active, Subscription.start_date <= day, Subscription.expiry_date >= day)
    elif state == SubscriptionState.upcoming:
        stmt = stmt.where(active, Subscription.start_date > day)
    elif state == SubscriptionState.expired:
        stmt = stmt.where(active, Subscription.expiry_date < day)
    elif state in (SubscriptionState.suspended, SubscriptionState.cancelled):
        stmt = stmt.where(Subscription.status == SubscriptionStatus(state.value))
    if expiring_within_days is not None:
        stmt = stmt.where(
            active,
            Subscription.start_date <= day,
            Subscription.expiry_date >= day,
            Subscription.expiry_date <= day + timedelta(days=expiring_within_days),
        )
        return stmt.order_by(Subscription.expiry_date)
    return stmt.order_by(Subscription.start_date.desc(), Subscription.id.desc())


def to_out(db: Session, subs: list[Subscription], day: date | None = None) -> list[SubscriptionOut]:
    day = day or today()
    ids = [s.id for s in subs]
    paid = (
        dict(
            db.execute(
                select(Payment.subscription_id, func.sum(Payment.amount))
                .where(Payment.subscription_id.in_(ids), Payment.status == PaymentStatus.paid)
                .group_by(Payment.subscription_id)
            ).all()
        )
        if ids
        else {}
    )
    out = []
    for s in subs:
        state = s.state_on(day)
        if state == SubscriptionState.active:
            remaining = (s.expiry_date - day).days + 1
        elif state == SubscriptionState.upcoming:
            remaining = (s.expiry_date - s.start_date).days + 1
        else:
            remaining = 0
        o = SubscriptionOut.model_validate(
            {
                **{c: getattr(s, c) for c in SubscriptionOut.model_fields if hasattr(s, c)},
                "state": state,
                "remaining_days": remaining,
                "amount_paid": paid.get(s.id, Decimal("0")),
            }
        )
        out.append(o)
    return out


def current_and_upcoming(db: Session, member_id: int, day: date) -> tuple[Subscription | None, Subscription | None]:
    active = Subscription.status == SubscriptionStatus.active
    current = db.scalar(
        select(Subscription)
        .where(
            Subscription.member_id == member_id, active, Subscription.start_date <= day, Subscription.expiry_date >= day
        )
        .order_by(Subscription.expiry_date.desc())
        .limit(1)
    )
    upcoming = db.scalar(
        select(Subscription)
        .where(Subscription.member_id == member_id, active, Subscription.start_date > day)
        .order_by(Subscription.start_date)
        .limit(1)
    )
    return current, upcoming


def latest(db: Session, member_id: int) -> Subscription | None:
    return db.scalar(
        select(Subscription)
        .where(Subscription.member_id == member_id, Subscription.status != SubscriptionStatus.cancelled)
        .order_by(Subscription.expiry_date.desc())
        .limit(1)
    )
