from datetime import date

from app.packages.models import DurationUnit, add_duration


def test_add_duration():
    assert add_duration(date(2026, 1, 1), 1, DurationUnit.months) == date(2026, 1, 31)
    assert add_duration(date(2026, 1, 31), 1, DurationUnit.months) == date(2026, 2, 27)
    assert add_duration(date(2026, 11, 15), 3, DurationUnit.months) == date(2027, 2, 14)
    assert add_duration(date(2026, 1, 1), 30, DurationUnit.days) == date(2026, 1, 30)


def test_assign_renew_history_and_snapshot(client, admin, freeze, make_package, make_member, subscribe):
    freeze("2026-03-10 10:00")
    p = make_package()
    m = make_member()
    s1 = subscribe(m["id"], p["id"], payment={"method": "upi"})
    assert (s1["start_date"], s1["expiry_date"], s1["state"]) == ("2026-03-10", "2026-04-09", "active")
    assert s1["remaining_days"] == 31 and s1["amount_paid"] == "1500.00"

    # overlapping assignment rejected
    r = client.post("/api/subscriptions", headers=admin, json={"member_id": m["id"], "package_id": p["id"]})
    assert r.status_code == 409

    # editing the package does not rewrite history
    client.patch(f"/api/packages/{p['id']}", headers=admin, json={"name": "Monthly Plus", "price": "1800"})
    r = client.post(f"/api/subscriptions/{s1['id']}/renew", headers=admin, json={})
    s2 = r.json()
    assert r.status_code == 201
    assert s2["start_date"] == "2026-04-10" and s2["renewed_from_id"] == s1["id"]
    assert s2["package_name"] == "Monthly Plus" and s2["amount"] == "1800.00" and s2["state"] == "upcoming"
    assert client.get(f"/api/subscriptions/{s1['id']}", headers=admin).json()["package_name"] == "Monthly"

    hist = client.get("/api/subscriptions", headers=admin, params={"member_id": m["id"]}).json()
    assert hist["total"] == 2


def test_lapsed_renewal_starts_today_and_states(client, admin, freeze, make_package, make_member, subscribe):
    freeze("2026-01-01 10:00")
    p = make_package(name="10 days", value=10, unit="days", price="500")
    m = make_member()
    s1 = subscribe(m["id"], p["id"])
    freeze("2026-02-01 10:00")
    assert client.get(f"/api/subscriptions/{s1['id']}", headers=admin).json()["state"] == "expired"
    r = client.get("/api/subscriptions", headers=admin, params={"state": "expired"}).json()
    assert r["total"] == 1
    s2 = client.post(f"/api/subscriptions/{s1['id']}/renew", headers=admin, json={}).json()
    assert s2["start_date"] == "2026-02-01" and s2["state"] == "active"


def test_inactive_package_cannot_be_assigned(client, admin, make_package, make_member):
    p = make_package()
    client.patch(f"/api/packages/{p['id']}", headers=admin, json={"is_active": False})
    m = make_member()
    r = client.post("/api/subscriptions", headers=admin, json={"member_id": m["id"], "package_id": p["id"]})
    assert r.status_code == 400


def test_member_sees_only_own_subscription_and_active_packages(
    client, admin, make_package, make_member, member_login, subscribe
):
    p = make_package()
    make_package(name="Old", is_active=False)
    a, b = make_member(), make_member()
    subscribe(a["id"], p["id"])
    subscribe(b["id"], p["id"])
    h = member_login(a)
    mine = client.get("/api/me/subscriptions", headers=h).json()
    assert [s["member_id"] for s in mine] == [a["id"]]
    assert client.get("/api/me/subscription", headers=h).json()["current"]["member_id"] == a["id"]
    assert [x["name"] for x in client.get("/api/packages/available", headers=h).json()] == ["Monthly"]
    assert client.get("/api/packages", headers=h).status_code == 403
    assert client.get(f"/api/subscriptions/{1}", headers=h).status_code == 403
