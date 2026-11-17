from app.common.database import SessionLocal
from app.notifications.service import generate_reminders


def _run():
    with SessionLocal() as db:
        return generate_reminders(db)


def test_reminders_7_and_1_days_then_expired(client, admin, freeze, make_package, make_member, subscribe, member_login):
    freeze("2026-03-01 08:00")
    p = make_package(name="10 days", value=10, unit="days", price="500")  # expires 2026-03-10
    m = make_member()
    subscribe(m["id"], p["id"])
    h = member_login(m)

    freeze("2026-03-03 08:00")
    _run()
    notes = client.get("/api/notifications", headers=h).json()["items"]
    assert [n["title"] for n in notes] == ["Your membership expires in 7 days"]
    _run()  # idempotent
    assert client.get("/api/notifications", headers=h).json()["total"] == 1

    freeze("2026-03-09 08:00")
    _run()
    freeze("2026-03-11 08:00")
    _run()
    titles = [n["title"] for n in client.get("/api/notifications", headers=h).json()["items"]]
    assert titles == [
        "Your membership has expired",
        "Your membership expires tomorrow",
        "Your membership expires in 7 days",
    ]
    assert client.get("/api/notifications/unread-count", headers=h).json()["unread"] == 3
    client.post("/api/notifications/read-all", headers=h)
    assert client.get("/api/notifications/unread-count", headers=h).json()["unread"] == 0
    # Admin received a digest
    assert client.get("/api/notifications", headers=admin).json()["total"] >= 1


def test_no_reminder_when_already_renewed(client, admin, freeze, make_package, make_member, subscribe, member_login):
    freeze("2026-03-01 08:00")
    p = make_package(name="10 days", value=10, unit="days", price="500")
    m = make_member()
    s = subscribe(m["id"], p["id"])
    client.post(f"/api/subscriptions/{s['id']}/renew", headers=admin, json={})
    freeze("2026-03-09 08:00")
    _run()
    assert client.get("/api/notifications", headers=member_login(m)).json()["total"] == 0


def test_configurable_schedule(client, admin, freeze, make_package, make_member, subscribe, member_login, monkeypatch):
    from app.common.config import get_settings

    monkeypatch.setenv("REMINDER_DAYS_BEFORE_EXPIRY", "[3]")
    get_settings.cache_clear()
    freeze("2026-03-01 08:00")
    p = make_package(name="10 days", value=10, unit="days", price="500")
    m = make_member()
    subscribe(m["id"], p["id"])
    freeze("2026-03-07 08:00")
    _run()
    notes = client.get("/api/notifications", headers=member_login(m)).json()["items"]
    assert [n["title"] for n in notes] == ["Your membership expires in 3 days"]


def test_admin_trigger_and_notification_isolation(client, admin, make_member, member_login):
    assert client.post("/api/notifications/run-reminders", headers=admin).status_code == 200
    m = make_member()
    h = member_login(m)
    assert client.post("/api/notifications/run-reminders", headers=h).status_code == 403
