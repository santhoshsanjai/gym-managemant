from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth.deps import DB, AdminUser, CurrentMember, require_admin
from app.common import audit
from app.common.pagination import Page, PageParams, paginate
from app.common.timeutil import today
from app.subscriptions import service
from app.subscriptions.models import SubscriptionState
from app.subscriptions.schemas import (
    SubscriptionCreate,
    SubscriptionOut,
    SubscriptionRenew,
    SubscriptionStatusUpdate,
    SubscriptionUpdate,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"], dependencies=[Depends(require_admin)])
me_router = APIRouter(prefix="/me", tags=["member self-service"])


@router.get("", response_model=Page[SubscriptionOut])
def list_subscriptions(
    db: DB,
    params: PageParams = Depends(),
    member_id: int | None = None,
    state: SubscriptionState | None = None,
    package_id: int | None = None,
    expiring_within_days: int | None = Query(None, ge=0, le=365),
):
    day = today()
    page = paginate(db, service.list_query(member_id, state, package_id, expiring_within_days, day), params)
    page["items"] = service.to_out(db, page["items"], day)
    return page


@router.post("", response_model=SubscriptionOut, status_code=201)
def create_subscription(body: SubscriptionCreate, db: DB, admin: AdminUser):
    return service.to_out(db, [service.create_subscription(db, body, admin)])[0]


@router.get("/{sub_id}", response_model=SubscriptionOut)
def get_subscription(sub_id: int, db: DB):
    return service.to_out(db, [service.get_subscription(db, sub_id)])[0]


@router.post("/{sub_id}/renew", response_model=SubscriptionOut, status_code=201)
def renew(sub_id: int, body: SubscriptionRenew, db: DB, admin: AdminUser):
    prev = service.get_subscription(db, sub_id)
    return service.to_out(db, [service.renew_subscription(db, prev, body, admin)])[0]


@router.patch("/{sub_id}", response_model=SubscriptionOut)
def update(sub_id: int, body: SubscriptionUpdate, db: DB, admin: AdminUser):
    from app.common.errors import bad_request

    s = service.get_subscription(db, sub_id)
    changes = body.model_dump(exclude_unset=True)
    start = changes.get("start_date") or s.start_date
    end = changes.get("expiry_date") or s.expiry_date
    if end < start:
        raise bad_request("expiry_date must be on or after start_date")
    if "start_date" in changes or "expiry_date" in changes:
        service._check_overlap(db, s.member_id, start, end, exclude_id=s.id)
    before = {k: getattr(s, k) for k in changes}
    for k, v in changes.items():
        if v is not None or k == "notes":
            setattr(s, k, v)
    audit.record(db, admin.id, "update", "subscription", s.id, before=before, after=changes)
    db.commit()
    return service.to_out(db, [s])[0]


@router.post("/{sub_id}/status", response_model=SubscriptionOut)
def set_status(sub_id: int, body: SubscriptionStatusUpdate, db: DB, admin: AdminUser):
    from app.subscriptions.models import SubscriptionStatus

    s = service.get_subscription(db, sub_id)
    if body.status == SubscriptionStatus.active and s.status != SubscriptionStatus.active:
        service._check_overlap(db, s.member_id, s.start_date, s.expiry_date, exclude_id=s.id)
    old = s.status
    s.status = body.status
    if body.notes is not None:
        s.notes = body.notes
    audit.record(db, admin.id, "set_status", "subscription", s.id, before=old.value, after=body.status.value)
    db.commit()
    return service.to_out(db, [s])[0]


# ---------------------------------------------------------------- self-service


class MySubscription(BaseModel):
    current: SubscriptionOut | None
    upcoming: SubscriptionOut | None
    latest: SubscriptionOut | None


@me_router.get("/subscription", response_model=MySubscription)
def my_subscription(member: CurrentMember, db: DB):
    day = today()
    current, upcoming = service.current_and_upcoming(db, member.id, day)
    last = service.latest(db, member.id)

    def one(s):
        return service.to_out(db, [s], day)[0] if s else None

    return MySubscription(current=one(current), upcoming=one(upcoming), latest=one(last))


@me_router.get("/subscriptions", response_model=list[SubscriptionOut])
def my_subscription_history(member: CurrentMember, db: DB):
    day = today()
    subs = db.scalars(service.list_query(member.id, None, None, None, day)).all()
    return service.to_out(db, list(subs), day)
