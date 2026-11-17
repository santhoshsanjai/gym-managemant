from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.models import Role, User
from app.common import audit
from app.common.errors import bad_request, conflict, not_found
from app.common.security import hash_password
from app.common.timeutil import today
from app.members.models import Member, MemberStatus
from app.members.schemas import MemberCreate
from app.subscriptions.models import Subscription, SubscriptionStatus
from app.subscriptions.queries import has_active_subscription, has_any_subscription, has_expired_membership
from app.trainers.models import Trainer, TrainerStatus


def get_member(db: Session, member_id: int) -> Member:
    m = db.get(Member, member_id)
    if m is None:
        raise not_found("Member")
    return m


def _check_trainer(db: Session, trainer_id: int | None) -> None:
    if trainer_id is None:
        return
    t = db.get(Trainer, trainer_id)
    if t is None:
        raise bad_request("Trainer does not exist")
    if t.status != TrainerStatus.active:
        raise bad_request("Trainer is inactive")


def _check_unique(db: Session, mobile: str | None, email: str | None, exclude_user_id: int | None = None) -> None:
    if mobile:
        q = select(User.id).where(func.lower(User.username) == mobile.lower())
        q2 = select(Member.id).where(Member.mobile == mobile)
        if exclude_user_id:
            q = q.where(User.id != exclude_user_id)
            q2 = q2.where(Member.user_id != exclude_user_id)
        if db.scalar(q) or db.scalar(q2):
            raise conflict("A member with this mobile number already exists")
    if email:
        q = select(User.id).where(func.lower(User.email) == email.lower())
        if exclude_user_id:
            q = q.where(User.id != exclude_user_id)
        if db.scalar(q):
            raise conflict("This email address is already in use")


def create_member(db: Session, data: MemberCreate, actor: User) -> Member:
    _check_unique(db, data.mobile, data.email)
    _check_trainer(db, data.trainer_id)
    user = User(
        username=data.mobile.lower(),
        email=data.email.lower() if data.email else None,
        password_hash=hash_password(data.password),
        role=Role.member,
        must_change_password=True,
    )
    db.add(user)
    db.flush()
    fields = data.model_dump(exclude={"password", "joining_date"})
    if fields.get("email"):
        fields["email"] = fields["email"].lower()
    member = Member(user_id=user.id, joining_date=data.joining_date or today(), **fields)
    db.add(member)
    db.flush()
    audit.record(db, actor.id, "create", "member", member.id, full_name=member.full_name)
    db.commit()
    db.refresh(member)
    return member


def update_member(db: Session, member: Member, changes: dict, actor: User) -> Member:
    user = db.get(User, member.user_id)
    if "email" in changes and changes["email"]:
        changes["email"] = changes["email"].lower()
    _check_unique(db, changes.get("mobile"), changes.get("email"), exclude_user_id=user.id)
    if "trainer_id" in changes and changes["trainer_id"] != member.trainer_id:
        _check_trainer(db, changes["trainer_id"])
    for k, v in changes.items():
        if k in ("full_name", "mobile") and v is None:
            continue
        setattr(member, k, v)
    if changes.get("mobile"):
        user.username = changes["mobile"].lower()
    if "email" in changes:
        user.email = changes["email"]
    audit.record(db, actor.id, "update", "member", member.id, fields=sorted(changes))
    db.commit()
    db.refresh(member)
    return member


def set_status(db: Session, member: Member, status: MemberStatus, actor: User) -> Member:
    user = db.get(User, member.user_id)
    member.status = status
    user.is_active = status == MemberStatus.active
    if not user.is_active:
        user.token_version += 1  # sign the member out everywhere
    audit.record(db, actor.id, "set_status", "member", member.id, status=status.value)
    db.commit()
    db.refresh(member)
    return member


def list_members_query(
    q: str | None,
    status: MemberStatus | None,
    trainer_id: int | None,
    membership: str | None,
    day: date,
):
    stmt = select(Member)
    if q:
        term = f"%{q.strip().lower()}%"
        conds = [
            func.lower(Member.full_name).like(term),
            Member.mobile.like(term),
            func.lower(func.coalesce(Member.email, "")).like(term),
        ]
        code = q.strip().upper()
        if code.startswith("GYM") and code[3:].isdigit():
            conds.append(Member.id == int(code[3:]))
        stmt = stmt.where(or_(*conds))
    if status:
        stmt = stmt.where(Member.status == status)
    if trainer_id:
        stmt = stmt.where(Member.trainer_id == trainer_id)
    if membership == "active":
        stmt = stmt.where(has_active_subscription(day))
    elif membership == "expired":
        stmt = stmt.where(has_expired_membership(day))
    elif membership == "none":
        stmt = stmt.where(~has_any_subscription())
    return stmt.order_by(Member.id.desc())


def annotate_membership(db: Session, members: list[Member], day: date) -> list[dict]:
    """Attach current membership state / expiry to each member for list views."""
    from app.members.schemas import MemberListItem

    ids = [m.id for m in members]
    subs: dict[int, list[Subscription]] = {}
    if ids:
        rows = db.scalars(
            select(Subscription)
            .where(Subscription.member_id.in_(ids), Subscription.status != SubscriptionStatus.cancelled)
            .order_by(Subscription.expiry_date.desc())
        ).all()
        for s in rows:
            subs.setdefault(s.member_id, []).append(s)
    out = []
    for m in members:
        item = MemberListItem.model_validate(m)
        state, current = membership_state(subs.get(m.id, []), day)
        item.membership_state = state
        if current:
            item.current_expiry_date = current.expiry_date
            item.current_package_name = current.package_name
        out.append(item)
    return out


def membership_state(subs: list[Subscription], day: date) -> tuple[str, Subscription | None]:
    from app.subscriptions.models import SubscriptionState

    active = [s for s in subs if s.state_on(day) == SubscriptionState.active]
    if active:
        return "active", max(active, key=lambda s: s.expiry_date)
    upcoming = [s for s in subs if s.state_on(day) == SubscriptionState.upcoming]
    if upcoming:
        return "upcoming", min(upcoming, key=lambda s: s.start_date)
    if subs:
        return "expired", max(subs, key=lambda s: s.expiry_date)
    return "none", None
