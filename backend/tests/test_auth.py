def test_login_and_me(client, admin):
    r = client.get("/api/auth/me", headers=admin)
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


def test_bad_password(client, admin):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_unauthenticated_and_member_forbidden_from_admin(client, make_member, member_login):
    assert client.get("/api/members").status_code == 401
    m = make_member()
    h = member_login(m)
    assert client.get("/api/members", headers=h).status_code == 403
    assert client.get("/api/dashboard/admin", headers=h).status_code == 403
    assert client.get("/api/reports/members.xlsx", headers=h).status_code == 403
    assert client.get("/api/attendance/qr/current", headers=h).status_code == 403


def test_member_must_change_password_and_old_token_revoked(client, make_member):
    m = make_member()
    r = client.post("/api/auth/login", json={"username": m["mobile"], "password": m["_password"]})
    body = r.json()
    assert body["must_change_password"] is True and body["role"] == "member"
    old = {"Authorization": f"Bearer {body['access_token']}"}
    r = client.post(
        "/api/auth/change-password",
        headers=old,
        json={"current_password": m["_password"], "new_password": "brand-new-pass"},
    )
    assert r.status_code == 200
    assert client.get("/api/auth/me", headers=old).status_code == 401
    new = {"Authorization": f"Bearer {r.json()['access_token']}"}
    me = client.get("/api/auth/me", headers=new).json()
    assert me["must_change_password"] is False and me["member_id"] == m["id"]


def test_deactivated_member_cannot_login(client, admin, make_member, member_login):
    m = make_member()
    h = member_login(m)
    client.post(f"/api/members/{m['id']}/status", headers=admin, json={"status": "inactive"})
    assert client.get("/api/auth/me", headers=h).status_code == 401
    r = client.post("/api/auth/login", json={"username": m["mobile"], "password": m["_password"]})
    assert r.status_code == 403


def test_login_rate_limit(client, admin, monkeypatch):
    from app.common.config import get_settings

    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("LOGIN_RATE_LIMIT", "3")
    get_settings.cache_clear()
    codes = [client.post("/api/auth/login", json={"username": "admin", "password": "x"}).status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]


def test_token_expires(client, admin, freeze, monkeypatch):
    from datetime import timedelta

    from app.common import timeutil
    from app.common.config import get_settings

    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    get_settings.cache_clear()
    freeze("2026-03-10 09:00")
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass-123"})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=h).status_code == 200
    timeutil.frozen_now += timedelta(minutes=31)
    assert client.get("/api/auth/me", headers=h).status_code == 401
