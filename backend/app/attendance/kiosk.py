"""Kiosk links: let a gym tablet show the rotating QR code without signing in
as an admin. A kiosk secret can only fetch the current QR payload."""

import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.attendance import service
from app.attendance.models import KioskDevice
from app.attendance.schemas import QrTokenOut
from app.auth.deps import DB, AdminUser, require_admin
from app.common import audit
from app.common.config import get_settings
from app.common.ratelimit import kiosk_rate_limit
from app.common.timeutil import now_utc

router = APIRouter(prefix="/kiosks", tags=["kiosk"], dependencies=[Depends(require_admin)])
public_router = APIRouter(prefix="/attendance", tags=["kiosk"])

_SEEN_EVERY = timedelta(minutes=5)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class KioskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class KioskOut(BaseModel):
    id: int
    name: str
    created_at: datetime
    last_seen_at: datetime | None
    revoked_at: datetime | None

    model_config = {"from_attributes": True}


class KioskCreated(KioskOut):
    token: str = Field(description="Shown once. Open /kiosk#<token> on the display device.")


@router.get("", response_model=list[KioskOut])
def list_kiosks(db: DB):
    return db.scalars(select(KioskDevice).order_by(KioskDevice.revoked_at.is_not(None), KioskDevice.id.desc())).all()


@router.post("", response_model=KioskCreated, status_code=201)
def create_kiosk(body: KioskCreate, db: DB, admin: AdminUser):
    token = secrets.token_urlsafe(32)
    k = KioskDevice(name=body.name.strip(), token_hash=_hash(token), created_by_id=admin.id)
    db.add(k)
    db.flush()
    audit.record(db, admin.id, "create", "kiosk", k.id, name=k.name)
    db.commit()
    return KioskCreated(**KioskOut.model_validate(k).model_dump(), token=token)


@router.delete("/{kiosk_id}", response_model=KioskOut)
def revoke_kiosk(kiosk_id: int, db: DB, admin: AdminUser):
    k = db.get(KioskDevice, kiosk_id)
    if k is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Kiosk not found")
    if k.revoked_at is None:
        k.revoked_at = now_utc()
        audit.record(db, admin.id, "revoke", "kiosk", k.id, name=k.name)
        db.commit()
    return k


@public_router.get("/qr/kiosk", response_model=QrTokenOut, dependencies=[Depends(kiosk_rate_limit)])
def kiosk_qr(db: DB, x_kiosk_token: str = Header(..., max_length=200)):
    k = db.scalar(select(KioskDevice).where(KioskDevice.token_hash == _hash(x_kiosk_token)))
    if k is None or k.revoked_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="This display link is invalid or was revoked")
    now = now_utc()
    if k.last_seen_at is None or now - k.last_seen_at > _SEEN_EVERY:
        k.last_seen_at = now
        db.commit()
    tok = service.current_qr_token(db, None)
    return QrTokenOut(
        qr_payload=service.QR_PREFIX + tok.token,
        expires_at=tok.expires_at,
        ttl_seconds=get_settings().qr_token_ttl_seconds,
        server_time=now,
    )
