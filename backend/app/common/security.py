from datetime import timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.common.config import get_settings
from app.common.timeutil import now_utc

_hasher = PasswordHasher()  # Argon2id with library-recommended parameters


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: int, role: str, token_version: int) -> tuple[str, int]:
    s = get_settings()
    expires_in = s.access_token_expire_minutes * 60
    now = now_utc()
    payload = {
        "sub": str(user_id),
        "role": role,
        "tv": token_version,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm), expires_in


def decode_access_token(token: str) -> dict:
    s = get_settings()
    # Expiry is checked against the application clock (``now_utc``) rather
    # than PyJWT's wall clock so it stays consistent with the rest of the app.
    payload = jwt.decode(
        token,
        s.jwt_secret,
        algorithms=[s.jwt_algorithm],
        options={"verify_exp": False, "verify_iat": False, "require": ["exp", "sub"]},
    )
    if int(payload["exp"]) < int(now_utc().timestamp()):
        raise jwt.ExpiredSignatureError("Signature has expired")
    return payload
