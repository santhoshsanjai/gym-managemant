from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.members.schemas import MOBILE_PATTERN, _clean_mobile
from app.trainers.models import TrainerStatus


class TrainerCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    mobile: str = Field(pattern=MOBILE_PATTERN)
    email: EmailStr | None = None
    specialization: str | None = Field(default=None, max_length=150)
    experience_years: int | None = Field(default=None, ge=0, le=80)
    notes: str | None = Field(default=None, max_length=2000)

    _mobile = field_validator("mobile", mode="before")(_clean_mobile)


class TrainerUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    mobile: str | None = Field(default=None, pattern=MOBILE_PATTERN)
    email: EmailStr | None = None
    specialization: str | None = Field(default=None, max_length=150)
    experience_years: int | None = Field(default=None, ge=0, le=80)
    notes: str | None = Field(default=None, max_length=2000)
    status: TrainerStatus | None = None

    _mobile = field_validator("mobile", mode="before")(_clean_mobile)


class TrainerOut(BaseModel):
    id: int
    trainer_code: str
    full_name: str
    mobile: str
    email: str | None
    specialization: str | None
    experience_years: int | None
    notes: str | None
    status: TrainerStatus
    assigned_members: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
