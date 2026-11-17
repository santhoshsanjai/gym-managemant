from io import BytesIO

from openpyxl import load_workbook


def test_payments_summary_and_filters(client, admin, freeze, make_package, make_member, subscribe):
    freeze("2026-03-10 10:00")
    p = make_package()
    m = make_member()
    s = subscribe(m["id"], p["id"], payment={"method": "cash", "amount": "1000"})
    r = client.post(
        "/api/payments",
        headers=admin,
        json={
            "member_id": m["id"],
            "subscription_id": s["id"],
            "amount": "500",
            "method": "upi",
            "reference": "UPI123",
        },
    )
    assert r.status_code == 201 and r.json()["package_name"] == "Monthly"
    client.post(
        "/api/payments",
        headers=admin,
        json={"member_id": m["id"], "amount": "300", "method": "cash", "status": "pending"},
    )
    client.post(
        "/api/payments",
        headers=admin,
        json={"member_id": m["id"], "amount": "999", "method": "cash", "payment_date": "2026-02-28"},
    )
    summary = client.get("/api/payments/summary", headers=admin, params={"year": 2026, "month": 3}).json()
    assert summary["total_paid"] == "1500.00" and summary["count_paid"] == 2
    assert summary["total_pending"] == "300.00"
    assert summary["by_method"] == {"cash": "1000.00", "upi": "500.00"}
    r = client.get("/api/payments", headers=admin, params={"year": 2026, "month": 3, "status": "paid"}).json()
    assert r["total"] == 2
    other = make_member()
    bad = client.post(
        "/api/payments",
        headers=admin,
        json={"member_id": other["id"], "subscription_id": s["id"], "amount": "1", "method": "cash"},
    )
    assert bad.status_code == 400


def test_monthly_payment_export(client, admin, freeze, make_package, make_member, subscribe):
    freeze("2026-03-10 10:00")
    p = make_package()
    m = make_member("Priya")
    subscribe(m["id"], p["id"], payment={"method": "card"})
    client.post(
        "/api/payments",
        headers=admin,
        json={"member_id": m["id"], "amount": "300", "method": "cash", "status": "pending"},
    )
    r = client.get("/api/reports/payments.xlsx", headers=admin, params={"year": 2026, "month": 3})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats")
    wb = load_workbook(BytesIO(r.content))
    rows = list(wb["Payments"].values)
    assert rows[0][3] == "Member Name" and len(rows) == 2  # paid only by default
    assert rows[1][3] == "Priya" and rows[1][7] == "Monthly"
    r = client.get("/api/reports/payments.xlsx", headers=admin, params={"year": 2026, "month": 3, "status": "all"})
    assert len(list(load_workbook(BytesIO(r.content))["Payments"].values)) == 3
    r = client.get("/api/reports/members.xlsx", headers=admin)
    rows = list(load_workbook(BytesIO(r.content))["Members"].values)
    assert rows[1][1] == "Priya" and rows[1][10] == "active"


def test_admin_dashboard(client, admin, freeze, make_package, make_member, subscribe):
    freeze("2026-03-01 10:00")
    p = make_package()
    short = make_package(name="Week", value=7, unit="days", price="400")
    a, b, c = make_member(), make_member(), make_member()
    make_member()  # never subscribed
    subscribe(a["id"], p["id"], payment={"method": "cash"})
    subscribe(b["id"], short["id"], payment={"method": "cash"})  # ends 03-07
    subscribe(c["id"], short["id"], start_date="2026-02-01")  # expired
    freeze("2026-03-05 10:00")
    d = client.get("/api/dashboard/admin", headers=admin).json()
    assert d["total_members"] == 4
    assert d["active_members"] == 2
    assert d["expired_members"] == 1
    assert d["monthly_revenue"] == "1900.00"
    assert d["new_members_this_month"] == 4
    assert [s["member_id"] for s in d["upcoming_expiries"]] == [b["id"]]
    assert [s["member_id"] for s in d["recently_expired"]] == [c["id"]]


def test_member_dashboard(client, admin, freeze, make_package, make_member, subscribe, member_login):
    freeze("2026-03-01 10:00")
    p = make_package()
    m = make_member()
    subscribe(m["id"], p["id"])
    h = member_login(m)
    d = client.get("/api/dashboard/member", headers=h).json()
    assert d["remaining_days"] == 31 and d["checked_in_today"] is False
    assert d["current_subscription"]["package_name"] == "Monthly"
    qr = client.get("/api/attendance/qr/current", headers=admin).json()["qr_payload"]
    client.post("/api/attendance/check-in", headers=h, json={"qr_payload": qr})
    d = client.get("/api/dashboard/member", headers=h).json()
    assert d["checked_in_today"] is True and d["total_attendance"] == 1
