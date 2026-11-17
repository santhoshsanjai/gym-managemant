"""Excel (.xlsx) report generation with OpenPyXL."""

from datetime import date
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.attendance.models import Attendance
from app.common.timeutil import month_bounds, today
from app.members.models import Member
from app.members.service import annotate_membership
from app.payments.models import Payment, PaymentStatus

HEADER_FILL = PatternFill("solid", fgColor="1F2937")
HEADER_FONT = Font(bold=True, color="FFFFFF")
MONEY = "#,##0.00"
DATE = "DD-MM-YYYY"


def _sheet(
    ws, headers: list[str], rows: list[list], money_cols: set[int] = frozenset(), date_cols: set[int] = frozenset()
):
    ws.append(headers)
    for c in ws[1]:
        c.fill, c.font, c.alignment = HEADER_FILL, HEADER_FONT, Alignment(vertical="center")
    for r in rows:
        ws.append(r)
    for idx in range(1, len(headers) + 1):
        letter = get_column_letter(idx)
        width = max([len(str(headers[idx - 1]))] + [len(str(r[idx - 1] or "")) for r in rows[:500]]) + 2
        ws.column_dimensions[letter].width = min(max(width, 10), 45)
        if idx in money_cols:
            for cell in ws[letter][1:]:
                cell.number_format = MONEY
        if idx in date_cols:
            for cell in ws[letter][1:]:
                cell.number_format = DATE
    ws.freeze_panes = "A2"
    if rows:
        ws.auto_filter.ref = ws.dimensions


def _save(wb: Workbook) -> bytes:
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def monthly_payments_xlsx(db: Session, year: int, month: int, status: PaymentStatus | None) -> bytes:
    start, end = month_bounds(year, month)
    stmt = select(Payment).where(Payment.payment_date >= start, Payment.payment_date < end)
    if status:
        stmt = stmt.where(Payment.status == status)
    payments = db.scalars(stmt.order_by(Payment.payment_date, Payment.id)).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Payments"
    headers = [
        "Payment ID",
        "Payment Date",
        "Member ID",
        "Member Name",
        "Mobile",
        "Email",
        "Trainer",
        "Package",
        "Subscription Start",
        "Subscription Expiry",
        "Amount",
        "Method",
        "Reference",
        "Status",
        "Notes",
    ]
    rows = []
    for p in payments:
        m, s = p.member, p.subscription
        rows.append(
            [
                p.id,
                p.payment_date,
                m.member_code,
                m.full_name,
                m.mobile,
                m.email,
                m.trainer.full_name if m.trainer else None,
                s.package_name if s else None,
                s.start_date if s else None,
                s.expiry_date if s else None,
                p.amount,
                p.method.value,
                p.reference,
                p.status.value,
                p.notes,
            ]
        )
    _sheet(ws, headers, rows, money_cols={11}, date_cols={2, 9, 10})

    # Summary sheet: totals per status and per method (paid only).
    sm = wb.create_sheet("Summary")
    totals: dict[str, Decimal] = {}
    by_method: dict[str, Decimal] = {}
    for p in payments:
        totals[p.status.value] = totals.get(p.status.value, Decimal(0)) + p.amount
        if p.status == PaymentStatus.paid:
            by_method[p.method.value] = by_method.get(p.method.value, Decimal(0)) + p.amount
    sm.append(["Report", f"Payments for {start:%B %Y}"])
    sm.append(["Status filter", status.value if status else "all"])
    sm.append(["Generated on", today()])
    sm.append([])
    sm.append(["Collected (paid)", totals.get("paid", Decimal(0))])
    for k in ("pending", "failed", "refunded"):
        if k in totals:
            sm.append([f"Total {k}", totals[k]])
    sm.append([])
    sm.append(["Paid by method", "Amount"])
    for k, v in sorted(by_method.items()):
        sm.append([k, v])
    for row in sm.iter_rows():
        for c in row:
            if isinstance(c.value, Decimal):
                c.number_format = MONEY
            if isinstance(c.value, date):
                c.number_format = DATE
    sm.column_dimensions["A"].width = 22
    sm.column_dimensions["B"].width = 28
    for c in sm["A"]:
        c.font = Font(bold=True)
    return _save(wb)


def members_xlsx(db: Session) -> bytes:
    day = today()
    members = db.scalars(select(Member).order_by(Member.id)).all()
    items = annotate_membership(db, list(members), day)
    wb = Workbook()
    ws = wb.active
    ws.title = "Members"
    headers = [
        "Member ID",
        "Full Name",
        "Mobile",
        "Email",
        "Gender",
        "Date of Birth",
        "Address",
        "Joining Date",
        "Trainer",
        "Account Status",
        "Membership",
        "Current Package",
        "Expiry Date",
    ]
    rows = [
        [
            i.member_code,
            i.full_name,
            i.mobile,
            i.email,
            i.gender.value if i.gender else None,
            i.date_of_birth,
            i.address,
            i.joining_date,
            i.trainer.full_name if i.trainer else None,
            i.status.value,
            i.membership_state,
            i.current_package_name,
            i.current_expiry_date,
        ]
        for i in items
    ]
    _sheet(ws, headers, rows, date_cols={6, 8, 13})
    return _save(wb)


def monthly_attendance_xlsx(db: Session, year: int, month: int) -> bytes:
    """Every check-in in the month, plus visits per member."""
    from app.common.config import get_settings

    tz = get_settings().tz
    start, end = month_bounds(year, month)
    rows_db = db.scalars(
        select(Attendance)
        .where(Attendance.attendance_date >= start, Attendance.attendance_date < end)
        .order_by(Attendance.attendance_date, Attendance.checked_in_at)
    ).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "Check-ins"
    headers = ["Date", "Time", "Member ID", "Member Name", "Mobile", "Trainer", "Source"]
    rows = [
        [
            a.attendance_date,
            a.checked_in_at.astimezone(tz).strftime("%H:%M"),
            a.member.member_code,
            a.member.full_name,
            a.member.mobile,
            a.member.trainer.full_name if a.member.trainer else None,
            "QR scan" if a.source.value == "qr" else "Manual",
        ]
        for a in rows_db
    ]
    _sheet(ws, headers, rows, date_cols={1})

    per_member: dict[int, list] = {}
    for a in rows_db:
        e = per_member.setdefault(a.member_id, [a.member.member_code, a.member.full_name, a.member.mobile, 0, None])
        e[3] += 1
        e[4] = a.attendance_date
    sm = wb.create_sheet("Visits per member")
    summary = sorted(per_member.values(), key=lambda r: (-r[3], r[1]))
    _sheet(sm, ["Member ID", "Member Name", "Mobile", "Visits", "Last Visit"], summary, date_cols={5})
    return _save(wb)
