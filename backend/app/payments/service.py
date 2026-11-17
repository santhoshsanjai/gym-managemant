from datetime import date

from sqlalchemy import extract, select

from app.common.timeutil import month_bounds
from app.payments.models import Payment, PaymentMethod, PaymentStatus


def list_query(
    member_id: int | None = None,
    status: PaymentStatus | None = None,
    method: PaymentMethod | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    year: int | None = None,
    month: int | None = None,
):
    stmt = select(Payment)
    if member_id:
        stmt = stmt.where(Payment.member_id == member_id)
    if status:
        stmt = stmt.where(Payment.status == status)
    if method:
        stmt = stmt.where(Payment.method == method)
    if year and month:
        start, end = month_bounds(year, month)
        stmt = stmt.where(Payment.payment_date >= start, Payment.payment_date < end)
    elif year:
        stmt = stmt.where(extract("year", Payment.payment_date) == year)
    if date_from:
        stmt = stmt.where(Payment.payment_date >= date_from)
    if date_to:
        stmt = stmt.where(Payment.payment_date <= date_to)
    return stmt.order_by(Payment.payment_date.desc(), Payment.id.desc())


def to_out(p: Payment):
    from app.payments.schemas import PaymentOut

    o = PaymentOut.model_validate(p)
    o.package_name = p.subscription.package_name if p.subscription else None
    return o
