from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import service as auth_service
from app.auth.deps import DB, AdminUser, CurrentMember, CurrentUser, require_admin
from app.common import audit
from app.common.config import get_settings
from app.common.pagination import Page, PageParams, paginate
from app.common.timeutil import today
from app.members import service
from app.members.models import MemberStatus
from app.members.schemas import (
    MemberCreate,
    MemberListItem,
    MemberOut,
    MemberSelfUpdate,
    MemberStatusUpdate,
    MemberUpdate,
    PasswordReset,
)

router = APIRouter(prefix="/members", tags=["members"], dependencies=[Depends(require_admin)])
me_router = APIRouter(prefix="/me", tags=["member self-service"])


@router.get("", response_model=Page[MemberListItem])
def list_members(
    db: DB,
    params: PageParams = Depends(),
    q: str | None = Query(None, max_length=100, description="Name, mobile, email or member code"),
    status: MemberStatus | None = None,
    trainer_id: int | None = None,
    membership: Literal["active", "expired", "none"] | None = None,
):
    day = today()
    page = paginate(db, service.list_members_query(q, status, trainer_id, membership, day), params)
    page["items"] = service.annotate_membership(db, page["items"], day)
    return page


@router.post("", response_model=MemberOut, status_code=201)
def create_member(body: MemberCreate, db: DB, admin: AdminUser):
    return service.create_member(db, body, admin)


@router.get("/{member_id}", response_model=MemberListItem)
def get_member(member_id: int, db: DB):
    return service.annotate_membership(db, [service.get_member(db, member_id)], today())[0]


@router.patch("/{member_id}", response_model=MemberOut)
def update_member(member_id: int, body: MemberUpdate, db: DB, admin: AdminUser):
    m = service.get_member(db, member_id)
    return service.update_member(db, m, body.model_dump(exclude_unset=True), admin)


@router.post("/{member_id}/status", response_model=MemberOut)
def set_member_status(member_id: int, body: MemberStatusUpdate, db: DB, admin: AdminUser):
    return service.set_status(db, service.get_member(db, member_id), body.status, admin)


@router.post("/{member_id}/reset-password", status_code=204)
def reset_member_password(member_id: int, body: PasswordReset, db: DB, admin: AdminUser):
    from app.auth.models import User

    m = service.get_member(db, member_id)
    user = db.get(User, m.user_id)
    auth_service.set_password(user, body.new_password, must_change=True)
    audit.record(db, admin.id, "reset_password", "member", m.id)
    db.commit()


# ---------------------------------------------------------------- self-service


@me_router.get("/profile", response_model=MemberOut)
def my_profile(member: CurrentMember):
    return member


@me_router.get("/profile/editable-fields", response_model=list[str])
def my_editable_fields(_: CurrentUser):
    return get_settings().member_editable_fields


@me_router.patch("/profile", response_model=MemberOut)
def update_my_profile(body: MemberSelfUpdate, member: CurrentMember, user: CurrentUser, db: DB):
    changes = body.model_dump(exclude_unset=True)
    allowed = set(get_settings().member_editable_fields)
    forbidden = sorted(set(changes) - allowed)
    if forbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=f"You are not allowed to change: {', '.join(forbidden)}")
    return service.update_member(db, member, changes, user)
