from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.packages.models import DurationUnit


class PackageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    duration_value: int = Field(gt=0, le=3650)
    duration_unit: DurationUnit
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool = True


class PackageUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    duration_value: int | None = Field(default=None, gt=0, le=3650)
    duration_unit: DurationUnit | None = None
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class PackageOut(BaseModel):
    id: int
    name: str
    duration_value: int
    duration_unit: DurationUnit
    price: Decimal
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PackagePublic(BaseModel):
    id: int
    name: str
    duration_value: int
    duration_unit: DurationUnit
    price: Decimal
    description: str | None

    model_config = {"from_attributes": True}
