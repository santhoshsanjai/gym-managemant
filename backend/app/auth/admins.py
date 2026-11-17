"""Admin account management (more than one front-desk login)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from app.auth import service
from app.auth.deps import DB, AdminUser, require_admin
from app.auth.models import Role, User
from app.common import audit
from app.common.security import hash_password

router = APIRouter(prefix="/admins", tags=["admin accounts"], dependencies=[Depends(require_admin)])


class AdminCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9_.@-]+$")
    email: EmailStr | None = None
    password: str = Field(min_length=8, max_length=128)


class AdminStatus(BaseModel):
    is_active: bool


class AdminPasswordReset(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class AdminOut(BaseModel):
    id: int
    username: str
    email: str | None
    is_active: bool
    must_change_password: bool
    created_at: datetime

    model_config = {"from_attributes": True}


def _get_admin(db, admin_id: int) -> User:
    u = db.get(User, admin_id)
    if u is None or u.role != Role.admin:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Admin not found")
    return u


@router.get("", response_model=list[AdminOut])
def list_admins(db: DB):
    return db.scalars(select(User).where(User.role == Role.admin).order_by(User.id)).all()


@router.post("", response_model=AdminOut, status_code=201)
def create_admin(body: AdminCreate, db: DB, admin: AdminUser):
    username = body.username.strip().lower()
    if db.scalar(select(User.id).where(func.lower(User.username) == username)):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="This username is already taken")
    email = body.email.lower() if body.email else None
    if email and db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="This email address is already in use")
    u = User(
        username=username,
        email=email,
        password_hash=hash_password(body.password),
        role=Role.admin,
        must_change_password=True,
    )
    db.add(u)
    db.flush()
    audit.record(db, admin.id, "create", "admin", u.id, username=username)
    db.commit()
    return u


@router.post("/{admin_id}/status", response_model=AdminOut)
def set_admin_status(admin_id: int, body: AdminStatus, db: DB, admin: AdminUser):
    u = _get_admin(db, admin_id)
    if not body.is_active:
        if u.id == admin.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="You can't deactivate your own account")
        active = db.scalar(
            select(func.count()).select_from(User).where(User.role == Role.admin, User.is_active.is_(True))
        )
        if u.is_active and active <= 1:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="At least one active admin is required")
        u.token_version += 1
    u.is_active = body.is_active
    audit.record(db, admin.id, "set_status", "admin", u.id, is_active=body.is_active)
    db.commit()
    return u


@router.post("/{admin_id}/reset-password", status_code=204)
def reset_admin_password(admin_id: int, body: AdminPasswordReset, db: DB, admin: AdminUser):
    u = _get_admin(db, admin_id)
    service.set_password(u, body.new_password, must_change=u.id != admin.id)
    audit.record(db, admin.id, "reset_password", "admin", u.id)
    db.commit()
