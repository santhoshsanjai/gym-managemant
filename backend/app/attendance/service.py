import secrets
from datetime import date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.attendance.models import Attendance, AttendanceSource, QrToken
from app.auth.models import User
from app.common.config import get_settings
from app.common.timeutil import gym_day, now_utc
from app.members.models import Member, MemberStatus
from app.subscriptions.models import Subscription
from app.subscriptions.queries import covers

QR_PREFIX = "GYMQR:"
# A token is replaced once less than this much lifetime remains, so the
# displayed code is always comfortably valid when scanned.
_REFRESH_MARGIN = timedelta(seconds=5)


def current_qr_token(db: Session, issued_by: User | None) -> QrToken:
    s = get_settings()
    now = now_utc()
    tok = db.scalar(
        select(QrToken).where(QrToken.expires_at > now + _REFRESH_MARGIN).order_by(QrToken.expires_at.desc()).limit(1)
    )
    if tok:
        return tok
    tok = QrToken(
        token=secrets.token_urlsafe(24),
        issued_at=now,
        expires_at=now + timedelta(seconds=s.qr_token_ttl_seconds),
        issued_by_id=issued_by.id if issued_by else None,
    )
    db.add(tok)
    # Housekeeping: tokens older than a day are never needed again.
    db.execute(
        delete(QrToken).where(
            QrToken.expires_at < now - timedelta(days=1),
            ~QrToken.id.in_(
                select(Attendance.qr_token_id).where(Attendance.qr_token_id.is_not(None)).scalar_subquery()
            ),
        )
    )
    db.commit()
    return tok


def _err(code: int, msg: str) -> HTTPException:
    return HTTPException(code, detail=msg)


def _parse_payload(payload: str) -> str:
    payload = payload.strip()
    if payload.startswith(QR_PREFIX):
        payload = payload[len(QR_PREFIX) :]
    return payload


def validate_token(db: Session, payload: str, at: datetime) -> QrToken:
    s = get_settings()
    token = _parse_payload(payload)
    tok = db.scalar(select(QrToken).where(QrToken.token == token)) if token else None
    if tok is None:
        raise _err(status.HTTP_400_BAD_REQUEST, "This is not a valid gym QR code.")
    if at > tok.expires_at + timedelta(seconds=s.qr_token_grace_seconds):
        raise _err(status.HTTP_400_BAD_REQUEST, "This QR code has expired. Please scan the code currently on display.")
    return tok


def _check_policy(db: Session, member: Member, day: date, enforce_subscription: bool) -> None:
    s = get_settings()
    if member.status != MemberStatus.active:
        raise _err(status.HTTP_403_FORBIDDEN, "Your membership account is inactive. Please contact the front desk.")
    if enforce_subscription and s.attendance_require_active_subscription:
        ok = db.scalar(select(Subscription.id).where(Subscription.member_id == member.id, covers(day)).limit(1))
        if not ok:
            raise _err(
                status.HTTP_403_FORBIDDEN,
                "You don't have an active subscription for today. Please renew at the front desk.",
            )
    if s.attendance_max_checkins_per_day > 0:
        count = db.scalar(
            select(func.count())
            .select_from(Attendance)
            .where(Attendance.member_id == member.id, Attendance.attendance_date == day)
        )
        if count >= s.attendance_max_checkins_per_day:
            raise _err(status.HTTP_409_CONFLICT, "You have already checked in today.")


def _lock_member(db: Session, member_id: int) -> Member:
    """Row lock serialises concurrent check-ins for the same member so the
    per-day limit can't be bypassed by double submits."""
    return db.scalar(select(Member).where(Member.id == member_id).with_for_update(of=Member))


def check_in(db: Session, member: Member, payload: str) -> Attendance:
    at = now_utc()  # server time only; never trust the device clock
    tok = validate_token(db, payload, at)
    day = gym_day(at)
    member = _lock_member(db, member.id)
    _check_policy(db, member, day, enforce_subscription=True)
    att = Attendance(
        member_id=member.id, attendance_date=day, checked_in_at=at, source=AttendanceSource.qr, qr_token_id=tok.id
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return att


def manual_entry(db: Session, member_id: int, day: date | None, actor: User) -> Attendance:
    """Admin-recorded attendance (e.g. phone camera broken). Subscription
    rules are not enforced, but the per-day limit still applies."""
    member = _lock_member(db, member_id)
    if member is None:
        raise _err(status.HTTP_404_NOT_FOUND, "Member not found")
    at = now_utc()
    day = day or gym_day(at)
    if day > gym_day(at):
        raise _err(status.HTTP_400_BAD_REQUEST, "Attendance cannot be recorded for a future date")
    _check_policy(db, member, day, enforce_subscription=False)
    att = Attendance(
        member_id=member.id,
        attendance_date=day,
        checked_in_at=at,
        source=AttendanceSource.manual,
        recorded_by_id=actor.id,
    )
    db.add(att)
    db.flush()
    from app.common import audit

    audit.record(db, actor.id, "manual_checkin", "attendance", att.id, member_id=member.id, day=day)
    db.commit()
    db.refresh(att)
    return att


def list_query(member_id: int | None, date_from: date | None, date_to: date | None):
    stmt = select(Attendance)
    if member_id:
        stmt = stmt.where(Attendance.member_id == member_id)
    if date_from:
        stmt = stmt.where(Attendance.attendance_date >= date_from)
    if date_to:
        stmt = stmt.where(Attendance.attendance_date <= date_to)
    return stmt.order_by(Attendance.checked_in_at.desc())
