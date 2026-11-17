from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.payments.models import PaymentMethod, PaymentStatus
from app.subscriptions.schemas import MemberBrief


class PaymentCreate(BaseModel):
    member_id: int
    subscription_id: int | None = None
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    payment_date: date | None = None
    method: PaymentMethod
    reference: str | None = Field(default=None, max_length=120)
    status: PaymentStatus = PaymentStatus.paid
    notes: str | None = Field(default=None, max_length=1000)


class PaymentUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    payment_date: date | None = None
    method: PaymentMethod | None = None
    reference: str | None = Field(default=None, max_length=120)
    status: PaymentStatus | None = None
    notes: str | None = Field(default=None, max_length=1000)


class PaymentOut(BaseModel):
    id: int
    member_id: int
    member: MemberBrief
    subscription_id: int | None
    package_name: str | None = None
    amount: Decimal
    payment_date: date
    method: PaymentMethod
    reference: str | None
    status: PaymentStatus
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentSummary(BaseModel):
    year: int
    month: int
    total_paid: Decimal
    count_paid: int
    total_pending: Decimal
    count_pending: int
    by_method: dict[str, Decimal]
