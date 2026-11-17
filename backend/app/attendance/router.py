from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.attendance import service
from app.attendance.models import Attendance
from app.attendance.schemas import (
    AttendanceOut,
    CheckInRequest,
    CheckInResponse,
    ManualAttendanceCreate,
    MyAttendancePage,
    QrTokenOut,
)
from app.auth.deps import DB, AdminUser, CurrentMember
from app.common import audit
from app.common.config import get_settings
from app.common.errors import not_found
from app.common.pagination import Page, PageParams, paginate
from app.common.ratelimit import checkin_rate_limit
from app.common.timeutil import month_bounds, now_utc, today

router = APIRouter(prefix="/attendance", tags=["attendance"])
me_router = APIRouter(prefix="/me", tags=["member self-service"])


@router.get("/qr/current", response_model=QrTokenOut)
def current_qr(db: DB, admin: AdminUser):
    """Token for the gym's display screen. The screen polls this endpoint and
    redraws the QR code whenever the payload changes."""
    tok = service.current_qr_token(db, admin)
    return QrTokenOut(
        qr_payload=service.QR_PREFIX + tok.token,
        expires_at=tok.expires_at,
        ttl_seconds=get_settings().qr_token_ttl_seconds,
        server_time=now_utc(),
    )


@router.post("/check-in", response_model=CheckInResponse, status_code=201, dependencies=[Depends(checkin_rate_limit)])
def check_in(body: CheckInRequest, db: DB, member: CurrentMember):
    att = service.check_in(db, member, body.qr_payload)
    return CheckInResponse(message=f"Welcome, {member.full_name}! Attendance recorded.", attendance=att)


@router.get("", response_model=Page[AttendanceOut])
def list_attendance(
    db: DB,
    _: AdminUser,
    params: PageParams = Depends(),
    member_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    on: date | None = Query(None, description="Shortcut for a single day"),
):
    if on:
        date_from = date_to = on
    return paginate(db, service.list_query(member_id, date_from, date_to), params)


@router.post("/manual", response_model=AttendanceOut, status_code=201)
def manual(body: ManualAttendanceCreate, db: DB, admin: AdminUser):
    return service.manual_entry(db, body.member_id, body.attendance_date, admin)


@router.delete("/{attendance_id}", status_code=204)
def delete_attendance(attendance_id: int, db: DB, admin: AdminUser):
    att = db.get(Attendance, attendance_id)
    if att is None:
        raise not_found("Attendance record")
    audit.record(db, admin.id, "delete", "attendance", att.id, member_id=att.member_id, day=att.attendance_date)
    db.delete(att)
    db.commit()


# ---------------------------------------------------------------- self-service


@me_router.get("/attendance", response_model=MyAttendancePage)
def my_attendance(
    db: DB,
    member: CurrentMember,
    params: PageParams = Depends(),
    year: int | None = Query(None, ge=2000, le=2100),
    month: int | None = Query(None, ge=1, le=12),
):
    date_from = date_to = None
    if year and month:
        start, end = month_bounds(year, month)
        date_from, date_to = start, end.fromordinal(end.toordinal() - 1)
    page = paginate(db, service.list_query(member.id, date_from, date_to), params)
    total_all = db.scalar(select(func.count()).select_from(Attendance).where(Attendance.member_id == member.id))
    return {**page, "total_all_time": total_all}


@me_router.get("/attendance/today", response_model=AttendanceOut | None)
def my_attendance_today(db: DB, member: CurrentMember):
    return db.scalar(
        select(Attendance)
        .where(Attendance.member_id == member.id, Attendance.attendance_date == today())
        .order_by(Attendance.checked_in_at)
        .limit(1)
    )
