from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.auth import service
from app.auth.deps import DB, CurrentUser
from app.auth.models import Role
from app.auth.schemas import ChangePasswordRequest, LoginRequest, TokenResponse, UserOut
from app.common import audit
from app.common.ratelimit import login_rate_limit
from app.common.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(login_rate_limit)])
def login(body: LoginRequest, db: DB):
    user = service.authenticate(db, body.username, body.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="This account is deactivated. Please contact the gym.")
    token, expires_in = create_access_token(user.id, user.role.value, user.token_version)
    return TokenResponse(
        access_token=token, expires_in=expires_in, role=user.role, must_change_password=user.must_change_password
    )


@router.post("/logout", status_code=204)
def logout(user: CurrentUser):
    """JWTs are stateless; the client discards its token. Provided for symmetry."""
    return None


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser, db: DB):
    out = UserOut.model_validate(user)
    if user.role == Role.member:
        from app.members.models import Member

        m = db.scalar(select(Member).where(Member.user_id == user.id))
        if m:
            out.member_id, out.full_name = m.id, m.full_name
    return out


@router.post("/change-password", response_model=TokenResponse)
def change_password(body: ChangePasswordRequest, user: CurrentUser, db: DB):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if body.current_password == body.new_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="New password must differ from the current one")
    service.set_password(user, body.new_password)
    audit.record(db, user.id, "change_password", "user", user.id)
    db.commit()
    token, expires_in = create_access_token(user.id, user.role.value, user.token_version)
    return TokenResponse(access_token=token, expires_in=expires_in, role=user.role, must_change_password=False)
