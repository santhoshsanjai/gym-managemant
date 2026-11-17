PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def test_admin_uploads_member_photo_and_replaces_it(client, admin, make_member):
    m = make_member()
    r = client.post(f"/api/members/{m['id']}/photo", headers=admin, files={"file": ("a.png", PNG, "image/png")})
    assert r.status_code == 200, r.text
    url = r.json()["photo_url"]
    assert url.startswith("/api/media/photos/") and url.endswith(".png")
    got = client.get(url)
    assert got.status_code == 200 and got.content == PNG and got.headers["content-type"] == "image/png"

    r = client.post(f"/api/members/{m['id']}/photo", headers=admin, files={"file": ("b.jpg", JPEG, "image/jpeg")})
    new = r.json()["photo_url"]
    assert new != url and client.get(url).status_code == 404  # old file removed

    r = client.delete(f"/api/members/{m['id']}/photo", headers=admin)
    assert r.json()["photo_url"] is None and client.get(new).status_code == 404


def test_photo_validation(client, admin, make_member, monkeypatch):
    from app.common.config import get_settings

    m = make_member()
    r = client.post(f"/api/members/{m['id']}/photo", headers=admin, files={"file": ("x.png", b"<svg/>", "image/png")})
    assert r.status_code == 400
    monkeypatch.setenv("MAX_PHOTO_BYTES", "32")
    get_settings.cache_clear()
    r = client.post(f"/api/members/{m['id']}/photo", headers=admin, files={"file": ("a.png", PNG, "image/png")})
    assert r.status_code == 413
    assert client.get("/api/media/photos/..%2F..%2Fetc%2Fpasswd").status_code == 404


def test_member_self_photo_respects_policy(client, make_member, member_login, monkeypatch):
    from app.common.config import get_settings

    m = make_member()
    h = member_login(m)
    r = client.post("/api/me/profile/photo", headers=h, files={"file": ("a.png", PNG, "image/png")})
    assert r.status_code == 200 and r.json()["photo_url"]
    monkeypatch.setenv("MEMBER_EDITABLE_FIELDS", '["address"]')
    get_settings.cache_clear()
    r = client.post("/api/me/profile/photo", headers=h, files={"file": ("a.png", PNG, "image/png")})
    assert r.status_code == 403


def test_admin_accounts(client, admin):
    r = client.post("/api/admins", headers=admin, json={"username": "frontdesk", "password": "desk-pass-1"})
    assert r.status_code == 201 and r.json()["must_change_password"] is True
    other = r.json()["id"]
    assert (
        client.post("/api/admins", headers=admin, json={"username": "frontdesk", "password": "x" * 8}).status_code
        == 409
    )
    assert len(client.get("/api/admins", headers=admin).json()) == 2

    me = client.get("/api/auth/me", headers=admin).json()["id"]
    assert client.post(f"/api/admins/{me}/status", headers=admin, json={"is_active": False}).status_code == 400

    login = client.post("/api/auth/login", json={"username": "frontdesk", "password": "desk-pass-1"})
    assert login.status_code == 200
    h2 = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert (
        client.post(f"/api/admins/{other}/status", headers=admin, json={"is_active": False}).json()["is_active"]
        is False
    )
    assert client.get("/api/auth/me", headers=h2).status_code == 401
    # the remaining admin is the last active one and can't be deactivated by anyone
    assert client.post(f"/api/admins/{me}/status", headers=admin, json={"is_active": False}).status_code == 400


def test_members_cannot_manage_admins(client, make_member, member_login):
    h = member_login(make_member())
    assert client.get("/api/admins", headers=h).status_code == 403
    assert client.get("/api/audit-logs", headers=h).status_code == 403


def test_audit_log_names_actor_and_filters(client, admin, make_member):
    m = make_member()
    client.patch(f"/api/members/{m['id']}", headers=admin, json={"address": "x"})
    page = client.get("/api/audit-logs", headers=admin, params={"entity": "member"}).json()
    assert [r["action"] for r in page["items"]] == ["update", "create"]
    assert page["items"][0]["actor_username"] == "admin"
    one = client.get("/api/audit-logs", headers=admin, params={"entity": "member", "action": "create"}).json()
    assert one["total"] == 1
