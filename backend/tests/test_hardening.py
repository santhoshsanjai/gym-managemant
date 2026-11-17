from datetime import timedelta
from io import BytesIO

import pytest
from openpyxl import load_workbook
from pydantic import ValidationError

from app.common import timeutil


def test_kiosk_link_shows_qr_and_can_be_revoked(
    client, admin, freeze, make_package, make_member, subscribe, member_login
):
    freeze("2026-03-10 07:00")
    r = client.post("/api/kiosks", headers=admin, json={"name": "Front door tablet"})
    assert r.status_code == 201
    k = r.json()
    token = k["token"]
    assert "token" not in client.get("/api/kiosks", headers=admin).json()[0]

    qr = client.get("/api/attendance/qr/kiosk", headers={"X-Kiosk-Token": token})
    assert qr.status_code == 200 and qr.json()["qr_payload"].startswith("GYMQR:")
    assert client.get("/api/kiosks", headers=admin).json()[0]["last_seen_at"] is not None

    # the payload works for a real check-in
    p = make_package()
    m = make_member()
    subscribe(m["id"], p["id"])
    r = client.post("/api/attendance/check-in", headers=member_login(m), json={"qr_payload": qr.json()["qr_payload"]})
    assert r.status_code == 201

    # a kiosk token is not an admin session
    assert client.get("/api/members", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert client.get("/api/attendance/qr/kiosk", headers={"X-Kiosk-Token": "nope"}).status_code == 401

    assert client.delete(f"/api/kiosks/{k['id']}", headers=admin).json()["revoked_at"] is not None
    assert client.get("/api/attendance/qr/kiosk", headers={"X-Kiosk-Token": token}).status_code == 401


def test_members_cannot_manage_kiosks(client, make_member, member_login):
    h = member_login(make_member())
    assert client.post("/api/kiosks", headers=h, json={"name": "x"}).status_code == 403


def test_rate_limit_ignores_forged_forwarded_for(client, admin, monkeypatch):
    from app.common.config import get_settings

    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("LOGIN_RATE_LIMIT", "2")
    get_settings.cache_clear()
    codes = [
        client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "x"},
            headers={"X-Forwarded-For": f"10.0.0.{i}"},
        ).status_code
        for i in range(3)
    ]
    assert codes == [401, 401, 429]


def test_production_requires_strong_secret(monkeypatch):
    from app.common.config import Settings

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "change-me-in-production")
    with pytest.raises(ValidationError):
        Settings()
    monkeypatch.setenv("JWT_SECRET", "x" * 40)
    assert Settings().environment == "production"


def test_member_sees_only_own_payments(client, admin, freeze, make_package, make_member, subscribe, member_login):
    freeze("2026-03-10 10:00")
    p = make_package()
    a, b = make_member(), make_member()
    subscribe(a["id"], p["id"], payment={"method": "upi"})
    subscribe(b["id"], p["id"], payment={"method": "cash"})
    mine = client.get("/api/me/payments", headers=member_login(a)).json()
    assert mine["total"] == 1 and mine["items"][0]["member_id"] == a["id"]
    assert mine["items"][0]["package_name"] == "Monthly"
    assert client.get("/api/me/payments", headers=admin).status_code == 403


def test_monthly_attendance_export(client, admin, freeze, make_member):
    freeze("2026-03-10 07:30")
    a, b = make_member("Asha"), make_member("Babu")
    client.post("/api/attendance/manual", headers=admin, json={"member_id": a["id"]})
    client.post("/api/attendance/manual", headers=admin, json={"member_id": b["id"]})
    timeutil.frozen_now += timedelta(days=1)
    client.post("/api/attendance/manual", headers=admin, json={"member_id": a["id"]})
    r = client.get("/api/reports/attendance.xlsx", headers=admin, params={"year": 2026, "month": 3})
    assert r.status_code == 200
    wb = load_workbook(BytesIO(r.content))
    checkins = list(wb["Check-ins"].values)
    assert len(checkins) == 4 and checkins[1][1] == "07:30" and checkins[1][3] in ("Asha", "Babu")
    per = list(wb["Visits per member"].values)
    assert per[1][1] == "Asha" and per[1][3] == 2
