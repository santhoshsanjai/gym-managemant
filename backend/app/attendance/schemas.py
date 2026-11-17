from datetime import date, datetime

from pydantic import BaseModel, Field

from app.attendance.models import AttendanceSource
from app.subscriptions.schemas import MemberBrief


class QrTokenOut(BaseModel):
    qr_payload: str
    expires_at: datetime
    ttl_seconds: int
    server_time: datetime


class CheckInRequest(BaseModel):
    qr_payload: str = Field(min_length=1, max_length=200, description="Raw text decoded from the gym QR code")


class AttendanceOut(BaseModel):
    id: int
    member_id: int
    member: MemberBrief
    attendance_date: date
    checked_in_at: datetime
    source: AttendanceSource

    model_config = {"from_attributes": True}


class CheckInResponse(BaseModel):
    message: str
    attendance: AttendanceOut


class ManualAttendanceCreate(BaseModel):
    member_id: int
    attendance_date: date | None = None


class MyAttendancePage(BaseModel):
    items: list[AttendanceOut]
    total: int
    page: int
    page_size: int
    total_all_time: int
