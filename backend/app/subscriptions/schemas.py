from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.packages.models import DurationUnit
from app.payments.models import PaymentMethod, PaymentStatus
from app.subscriptions.models import SubscriptionState, SubscriptionStatus


class InlinePayment(BaseModel):
    """Optionally record the payment in the same request as the subscription."""

    amount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    payment_date: date | None = None
    method: PaymentMethod = PaymentMethod.cash
    reference: str | None = Field(default=None, max_length=120)
    status: PaymentStatus = PaymentStatus.paid
    notes: str | None = Field(default=None, max_length=1000)


class SubscriptionCreate(BaseModel):
    member_id: int
    package_id: int
    start_date: date | None = None
    amount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    notes: str | None = Field(default=None, max_length=1000)
    payment: InlinePayment | None = None


class SubscriptionRenew(BaseModel):
    package_id: int | None = None
    start_date: date | None = None
    amount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    notes: str | None = Field(default=None, max_length=1000)
    payment: InlinePayment | None = None


class SubscriptionUpdate(BaseModel):
    """Admin correction of an existing record (audited)."""

    start_date: date | None = None
    expiry_date: date | None = None
    amount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _order(self):
        if self.start_date and self.expiry_date and self.expiry_date < self.start_date:
            raise ValueError("expiry_date must be on or after start_date")
        return self


class SubscriptionStatusUpdate(BaseModel):
    status: SubscriptionStatus
    notes: str | None = Field(default=None, max_length=1000)


class MemberBrief(BaseModel):
    id: int
    member_code: str
    full_name: str
    mobile: str

    model_config = {"from_attributes": True}


class SubscriptionOut(BaseModel):
    id: int
    member_id: int
    member: MemberBrief
    package_id: int
    package_name: str
    duration_value: int
    duration_unit: DurationUnit
    start_date: date
    expiry_date: date
    amount: Decimal
    status: SubscriptionStatus
    state: SubscriptionState
    remaining_days: int
    renewed_from_id: int | None
    notes: str | None
    amount_paid: Decimal = Decimal("0")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
