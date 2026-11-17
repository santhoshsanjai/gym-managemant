from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.auth.deps import DB, AdminUser, require_admin
from app.common import audit
from app.common.timeutil import today
from app.payments.models import PaymentStatus
from app.reports import service

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_admin)])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _file(content: bytes, filename: str) -> Response:
    return Response(content, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/payments.xlsx", response_class=Response, responses={200: {"content": {XLSX: {}}}})
def monthly_payments(
    db: DB,
    admin: AdminUser,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    status: Literal["paid", "pending", "failed", "refunded", "all"] = Query(
        "paid", description="Payment status to include; revenue reports use 'paid'"
    ),
):
    data = service.monthly_payments_xlsx(db, year, month, None if status == "all" else PaymentStatus(status))
    audit.record(db, admin.id, "export", "report", "payments", year=year, month=month)
    db.commit()
    return _file(data, f"payments-{year}-{month:02d}.xlsx")


@router.get("/members.xlsx", response_class=Response, responses={200: {"content": {XLSX: {}}}})
def members(db: DB, admin: AdminUser):
    data = service.members_xlsx(db)
    audit.record(db, admin.id, "export", "report", "members")
    db.commit()
    return _file(data, f"members-{today().isoformat()}.xlsx")
