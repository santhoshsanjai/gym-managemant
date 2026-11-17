from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.auth.deps import DB, AdminUser, CurrentMember, require_admin
from app.common import audit
from app.common.errors import bad_request, not_found
from app.common.pagination import Page, PageParams, paginate
from app.common.timeutil import month_bounds, today
from app.members.models import Member
from app.payments import service
from app.payments.models import Payment, PaymentMethod, PaymentStatus
from app.payments.schemas import PaymentCreate, PaymentOut, PaymentSummary, PaymentUpdate
from app.subscriptions.models import Subscription

router = APIRouter(prefix="/payments", tags=["payments"], dependencies=[Depends(require_admin)])
me_router = APIRouter(prefix="/me", tags=["member self-service"])


@router.get("", response_model=Page[PaymentOut])
def list_payments(
    db: DB,
    params: PageParams = Depends(),
    member_id: int | None = None,
    status: PaymentStatus | None = None,
    method: PaymentMethod | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    year: int | None = Query(None, ge=2000, le=2100),
    month: int | None = Query(None, ge=1, le=12),
):
    page = paginate(db, service.list_query(member_id, status, method, date_from, date_to, year, month), params)
    page["items"] = [service.to_out(p) for p in page["items"]]
    return page


@router.get("/summary", response_model=PaymentSummary)
def monthly_summary(db: DB, year: int = Query(..., ge=2000, le=2100), month: int = Query(..., ge=1, le=12)):
    start, end = month_bounds(year, month)
    in_month = (Payment.payment_date >= start, Payment.payment_date < end)
    rows = db.execute(
        select(Payment.status, func.count(), func.coalesce(func.sum(Payment.amount), 0))
        .where(*in_month)
        .group_by(Payment.status)
    ).all()
    by_status = {s: (c, t) for s, c, t in rows}
    by_method = dict(
        db.execute(
            select(Payment.method, func.sum(Payment.amount))
            .where(*in_month, Payment.status == PaymentStatus.paid)
            .group_by(Payment.method)
        ).all()
    )
    paid = by_status.get(PaymentStatus.paid, (0, Decimal(0)))
    pending = by_status.get(PaymentStatus.pending, (0, Decimal(0)))
    return PaymentSummary(
        year=year,
        month=month,
        total_paid=paid[1],
        count_paid=paid[0],
        total_pending=pending[1],
        count_pending=pending[0],
        by_method={m.value: v for m, v in by_method.items()},
    )


@router.post("", response_model=PaymentOut, status_code=201)
def record_payment(body: PaymentCreate, db: DB, admin: AdminUser):
    if db.get(Member, body.member_id) is None:
        raise not_found("Member")
    if body.subscription_id:
        sub = db.get(Subscription, body.subscription_id)
        if sub is None:
            raise not_found("Subscription")
        if sub.member_id != body.member_id:
            raise bad_request("Subscription does not belong to this member")
    p = Payment(
        **body.model_dump(exclude={"payment_date"}), payment_date=body.payment_date or today(), recorded_by_id=admin.id
    )
    db.add(p)
    db.flush()
    audit.record(db, admin.id, "create", "payment", p.id, member_id=p.member_id, amount=p.amount, status=p.status.value)
    db.commit()
    db.refresh(p)
    return service.to_out(p)


@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: int, db: DB):
    p = db.get(Payment, payment_id)
    if p is None:
        raise not_found("Payment")
    return service.to_out(p)


@router.patch("/{payment_id}", response_model=PaymentOut)
def update_payment(payment_id: int, body: PaymentUpdate, db: DB, admin: AdminUser):
    """Correct a payment record. Payments are never deleted; mark them failed
    or refunded instead so the audit trail stays complete."""
    p = db.get(Payment, payment_id)
    if p is None:
        raise not_found("Payment")
    changes = body.model_dump(exclude_unset=True)
    before = {k: getattr(p, k) for k in changes}
    for k, v in changes.items():
        if v is not None or k in ("reference", "notes"):
            setattr(p, k, v)
    audit.record(db, admin.id, "update", "payment", p.id, before=before, after=changes)
    db.commit()
    db.refresh(p)
    return service.to_out(p)


@me_router.get("/payments", response_model=Page[PaymentOut])
def my_payments(db: DB, member: CurrentMember, params: PageParams = Depends()):
    """The signed-in member's own payment records (read-only)."""
    page = paginate(db, service.list_query(member_id=member.id), params)
    page["items"] = [service.to_out(p) for p in page["items"]]
    return page
