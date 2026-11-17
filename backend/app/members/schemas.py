from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator

from app.members.models import Gender, MemberStatus

MOBILE_PATTERN = r"^\+?[0-9]{7,15}$"


def _clean_mobile(v: str | None) -> str | None:
    if v is None:
        return v
    return v.replace(" ", "").replace("-", "")


class TrainerBrief(BaseModel):
    id: int
    full_name: str
    mobile: str
    specialization: str | None = None

    model_config = {"from_attributes": True}


class MemberBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    mobile: str = Field(pattern=MOBILE_PATTERN)
    email: EmailStr | None = None
    gender: Gender | None = None
    date_of_birth: date | None = None
    address: str | None = Field(default=None, max_length=1000)
    photo_url: str | None = Field(default=None, max_length=500)
    trainer_id: int | None = None

    _mobile = field_validator("mobile", mode="before")(_clean_mobile)


class MemberCreate(MemberBase):
    joining_date: date | None = None
    password: str = Field(min_length=8, max_length=128, description="Initial password; member must change it")


class MemberUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    mobile: str | None = Field(default=None, pattern=MOBILE_PATTERN)
    email: EmailStr | None = None
    gender: Gender | None = None
    date_of_birth: date | None = None
    address: str | None = Field(default=None, max_length=1000)
    photo_url: str | None = Field(default=None, max_length=500)
    trainer_id: int | None = None
    joining_date: date | None = None

    _mobile = field_validator("mobile", mode="before")(_clean_mobile)


class MemberSelfUpdate(BaseModel):
    """Fields a member may try to change; the allowed subset is configured by
    ``MEMBER_EDITABLE_FIELDS``."""

    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    email: EmailStr | None = None
    gender: Gender | None = None
    date_of_birth: date | None = None
    address: str | None = Field(default=None, max_length=1000)
    photo_url: str | None = Field(default=None, max_length=500)


class MemberStatusUpdate(BaseModel):
    status: MemberStatus


class PasswordReset(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class MemberOut(BaseModel):
    id: int
    member_code: str
    full_name: str
    mobile: str
    email: str | None
    gender: Gender | None
    date_of_birth: date | None
    address: str | None
    photo_url: str | None
    joining_date: date
    trainer_id: int | None
    trainer: TrainerBrief | None
    status: MemberStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemberListItem(MemberOut):
    membership_state: str = "none"  # active | expired | upcoming | none
    current_expiry_date: date | None = None
    current_package_name: str | None = None

    @computed_field
    @property
    def has_active_membership(self) -> bool:
        return self.membership_state == "active"
