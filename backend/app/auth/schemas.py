from pydantic import BaseModel, Field

from app.auth.models import Role


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255, description="Username, mobile number or email")
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: Role
    must_change_password: bool


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str
    email: str | None
    role: Role
    is_active: bool
    must_change_password: bool
    member_id: int | None = None
    full_name: str | None = None

    model_config = {"from_attributes": True}
