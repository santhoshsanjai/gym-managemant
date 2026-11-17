from datetime import timedelta

from app.common import timeutil


def _qr(client, admin):
    r = client.get("/api/attendance/qr/current", headers=admin)
    assert r.status_code == 200
    return r.json()["qr_payload"]


def _setup(freeze, make_package, make_member, subscribe, member_login, start="2026-03-10"):
    freeze(f"{start} 07:00")
    p = make_package()
    m = make_member()
    subscribe(m["id"], p["id"])
    return m, member_login(m)


def test_check_in_once_per_day(client, admin, freeze, make_package, make_member, subscribe, member_login):
    m, h = _setup(freeze, make_package, make_member, subscribe, member_login)
    qr = _qr(client, admin)
    r = client.post("/api/attendance/check-in", headers=h, json={"qr_payload": qr})
    assert r.status_code == 201, r.text
    assert r.json()["attendance"]["attendance_date"] == "2026-03-10"
    assert r.json()["attendance"]["source"] == "qr"
    r = client.post("/api/attendance/check-in", headers=h, json={"qr_payload": qr})
    assert r.status_code == 409
    # Next gym day is allowed again
    freeze("2026-03-11 06:00")
    r = client.post("/api/attendance/check-in", headers=h, json={"qr_payload": _qr(client, admin)})
    assert r.status_code == 201
    assert client.get("/api/me/attendance", headers=h).json()["total_all_time"] == 2


def test_rejects_arbitrary_and_expired_qr(client, admin, freeze, make_package, make_member, subscribe, member_login):
    m, h = _setup(freeze, make_package, make_member, subscribe, member_login)
    r = client.post("/api/attendance/check-in", headers=h, json={"qr_payload": "GYMQR:made-up"})
    assert r.status_code == 400
    qr = _qr(client, admin)
    # within TTL + grace still fine; beyond is rejected
    timeutil.frozen_now += timedelta(seconds=60 + 15 + 1)
    r = client.post("/api/attendance/check-in", headers=h, json={"qr_payload": qr})
    assert r.status_code == 400 and "expired" in r.json()["detail"]


def test_qr_rotates(client, admin, freeze):
    freeze("2026-03-10 07:00")
    a = _qr(client, admin)
    assert _qr(client, admin) == a
    timeutil.frozen_now += timedelta(seconds=56)
    assert _qr(client, admin) != a


def test_expired_subscription_blocked_and_configurable(
    client, admin, freeze, make_package, make_member, subscribe, member_login, monkeypatch
):
    from app.common.config import get_settings

    m, h = _setup(freeze, make_package, make_member, subscribe, member_login, start="2026-01-01")
    freeze("2026-02-01 09:00")  # monthly sub ended 2026-01-31
    r = client.post("/api/attendance/check-in", headers=h, json={"qr_payload": _qr(client, admin)})
    assert r.status_code == 403 and "subscription" in r.json()["detail"]

    monkeypatch.setenv("ATTENDANCE_REQUIRE_ACTIVE_SUBSCRIPTION", "false")
    get_settings.cache_clear()
    r = client.post("/api/attendance/check-in", headers=h, json={"qr_payload": _qr(client, admin)})
    assert r.status_code == 201


def test_multiple_checkins_when_configured(
    client, admin, freeze, make_package, make_member, subscribe, member_login, monkeypatch
):
    from app.common.config import get_settings

    m, h = _setup(freeze, make_package, make_member, subscribe, member_login)
    monkeypatch.setenv("ATTENDANCE_MAX_CHECKINS_PER_DAY", "2")
    get_settings.cache_clear()
    codes = [
        client.post("/api/attendance/check-in", headers=h, json={"qr_payload": _qr(client, admin)}).status_code
        for _ in range(3)
    ]
    assert codes == [201, 201, 409]


def test_gym_day_uses_gym_timezone_and_start_hour(
    client, admin, freeze, make_package, make_member, subscribe, member_login, monkeypatch
):
    from app.common.config import get_settings

    m, h = _setup(freeze, make_package, make_member, subscribe, member_login)
    monkeypatch.setenv("GYM_DAY_START_HOUR", "4")
    get_settings.cache_clear()
    freeze("2026-03-11 02:30")  # before 04:00 -> still 10 March
    r = client.post("/api/attendance/check-in", headers=h, json={"qr_payload": _qr(client, admin)})
    assert r.json()["attendance"]["attendance_date"] == "2026-03-10"


def test_admin_lists_and_members_isolated(client, admin, freeze, make_package, make_member, subscribe, member_login):
    a, ha = _setup(freeze, make_package, make_member, subscribe, member_login)
    b = make_member()
    client.post("/api/subscriptions", headers=admin, json={"member_id": b["id"], "package_id": 1})
    hb = member_login(b)
    qr = _qr(client, admin)
    client.post("/api/attendance/check-in", headers=ha, json={"qr_payload": qr})
    client.post("/api/attendance/check-in", headers=hb, json={"qr_payload": qr})
    assert client.get("/api/attendance", headers=admin, params={"on": "2026-03-10"}).json()["total"] == 2
    assert client.get("/api/attendance", headers=admin, params={"member_id": a["id"]}).json()["total"] == 1
    mine = client.get("/api/me/attendance", headers=ha).json()
    assert {x["member_id"] for x in mine["items"]} == {a["id"]}
    assert client.get("/api/attendance", headers=ha).status_code == 403
    assert client.get("/api/me/attendance/today", headers=ha).json()["member_id"] == a["id"]


def test_manual_entry(client, admin, freeze, make_member):
    freeze("2026-03-10 07:00")
    m = make_member()
    r = client.post("/api/attendance/manual", headers=admin, json={"member_id": m["id"]})
    assert r.status_code == 201 and r.json()["source"] == "manual"
    assert client.post("/api/attendance/manual", headers=admin, json={"member_id": m["id"]}).status_code == 409
    r = client.post(
        "/api/attendance/manual", headers=admin, json={"member_id": m["id"], "attendance_date": "2026-03-12"}
    )
    assert r.status_code == 400
