def test_member_crud_search_and_uniqueness(client, admin, make_member):
    a = make_member("Priya Sharma", email="priya@example.com")
    make_member("Rahul Mehta")
    assert a["member_code"] == f"GYM{a['id']:05d}"

    r = client.get("/api/members", headers=admin, params={"q": "priya"})
    assert r.json()["total"] == 1
    r = client.get("/api/members", headers=admin, params={"q": a["member_code"]})
    assert [x["id"] for x in r.json()["items"]] == [a["id"]]

    dup = client.post(
        "/api/members", headers=admin, json={"full_name": "X", "mobile": a["mobile"], "password": "password1"}
    )
    assert dup.status_code == 409

    r = client.patch(f"/api/members/{a['id']}", headers=admin, json={"address": "12 MG Road", "mobile": "9111111111"})
    assert r.status_code == 200 and r.json()["address"] == "12 MG Road"
    # login identifier follows the mobile number
    assert (
        client.post("/api/auth/login", json={"username": "9111111111", "password": a["_password"]}).status_code == 200
    )


def test_member_self_profile_rules(client, make_member, member_login, monkeypatch):
    m = make_member()
    h = member_login(m)
    assert client.patch("/api/me/profile", headers=h, json={"address": "New addr"}).status_code == 200
    r = client.patch("/api/me/profile", headers=h, json={"full_name": "Hacker"})
    assert r.status_code == 403
    # Admin-controlled fields aren't even part of the self-update schema
    r = client.patch("/api/me/profile", headers=h, json={"status": "active", "joining_date": "2020-01-01"})
    assert r.status_code == 200
    assert client.get("/api/me/profile", headers=h).json()["joining_date"] != "2020-01-01"


def test_trainer_assignment_and_delete_rules(client, admin, make_member):
    t = client.post("/api/trainers", headers=admin, json={"full_name": "Arun", "mobile": "9000000001"}).json()
    m = make_member(trainer_id=t["id"])
    assert m["trainer"]["full_name"] == "Arun"
    assert client.get(f"/api/trainers/{t['id']}", headers=admin).json()["assigned_members"] == 1
    assert client.delete(f"/api/trainers/{t['id']}", headers=admin).status_code == 409
    r = client.patch(f"/api/trainers/{t['id']}", headers=admin, json={"status": "inactive"})
    assert r.json()["status"] == "inactive"
    # inactive trainers can't receive new members
    r = client.post(
        "/api/members",
        headers=admin,
        json={"full_name": "Y", "mobile": "9222222222", "password": "password1", "trainer_id": t["id"]},
    )
    assert r.status_code == 400
    t2 = client.post("/api/trainers", headers=admin, json={"full_name": "B", "mobile": "9000000002"}).json()
    assert client.delete(f"/api/trainers/{t2['id']}", headers=admin).status_code == 204
