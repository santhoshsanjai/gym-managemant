from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import Role, User
from app.common.database import get_db
from app.members.models import Member

_bearer = HTTPBearer(auto_error=False)

DB = Annotated[Session, Depends(get_db)]


def _unauthorized(msg: str = "Not authenticated") -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail=msg, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> User:
    from app.common.security import decode_access_token

    if creds is None:
        raise _unauthorized()
    try:
        payload = decode_access_token(creds.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _unauthorized("Invalid or expired token")
    user = db.get(User, user_id)
    if user is None or not user.is_active or user.token_version != payload.get("tv"):
        raise _unauthorized("Session is no longer valid")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != Role.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def get_current_member(user: CurrentUser, db: DB) -> Member:
    if user.role != Role.member:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Member access required")
    member = db.scalar(select(Member).where(Member.user_id == user.id))
    if member is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="No member profile linked to this account")
    return member


CurrentMember = Annotated[Member, Depends(get_current_member)]
