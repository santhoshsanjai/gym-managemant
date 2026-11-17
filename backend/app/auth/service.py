from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.models import Role, User
from app.common.security import hash_password, verify_password

# Verifying against a dummy hash keeps response time similar for unknown users.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def authenticate(db: Session, identifier: str, password: str) -> User | None:
    ident = identifier.strip().lower()
    user = db.scalar(select(User).where(or_(func.lower(User.username) == ident, func.lower(User.email) == ident)))
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def set_password(user: User, new_password: str, must_change: bool = False) -> None:
    user.password_hash = hash_password(new_password)
    user.must_change_password = must_change
    user.token_version += 1


def ensure_admin(db: Session, username: str, password: str) -> User:
    """Create an admin account if no admin exists (idempotent)."""
    existing = db.scalar(select(User).where(User.role == Role.admin).limit(1))
    if existing:
        return existing
    user = User(username=username.strip().lower(), password_hash=hash_password(password), role=Role.admin)
    db.add(user)
    db.commit()
    return user
