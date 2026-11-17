import os
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://gym:gym@localhost:5432/gym_test")
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["MEDIA_DIR"] = os.path.join(os.path.dirname(__file__), ".media-test")
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret"
os.environ["BOOTSTRAP_ADMIN_USERNAME"] = ""
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = str(60 * 24 * 365)  # tests move the clock by days

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.common import timeutil  # noqa: E402
from app.common.config import get_settings  # noqa: E402
from app.common.database import Base, SessionLocal, engine  # noqa: E402
from app.common.ratelimit import limiter  # noqa: E402

HERE = os.path.dirname(os.path.dirname(__file__))


@pytest.fixture(scope="session", autouse=True)
def _schema():
    with engine.begin() as c:
        c.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    cfg = Config(os.path.join(HERE, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(HERE, "alembic"))
    command.upgrade(cfg, "head")  # exercises the real migration
    yield


@pytest.fixture(autouse=True)
def _clean(_schema):
    yield
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as c:
        c.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    timeutil.frozen_now = None
    limiter.reset()
    get_settings.cache_clear()


@pytest.fixture
def freeze():
    """freeze("2026-03-10 09:00") -> fixes server time (given in gym local time)."""

    def _f(local: str):
        dt = datetime.fromisoformat(local).replace(tzinfo=get_settings().tz)
        timeutil.frozen_now = dt.astimezone(timezone.utc)
        return timeutil.frozen_now

    return _f


@pytest.fixture
def db():
    with SessionLocal() as s:
        yield s


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


def _login(client, username, password):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin(client, db):
    from app.auth.service import ensure_admin

    ensure_admin(db, "admin", "admin-pass-123")
    return _login(client, "admin", "admin-pass-123")


@pytest.fixture
def make_package(client, admin):
    def _p(name="Monthly", value=1, unit="months", price="1500.00", **kw):
        r = client.post(
            "/api/packages",
            headers=admin,
            json={"name": name, "duration_value": value, "duration_unit": unit, "price": price, **kw},
        )
        assert r.status_code == 201, r.text
        return r.json()

    return _p


@pytest.fixture
def make_member(client, admin):
    counter = {"n": 0}

    def _m(name=None, password="member-pass-1", **kw):
        counter["n"] += 1
        body = {
            "full_name": name or f"Member {counter['n']}",
            "mobile": f"98765{counter['n']:05d}",
            "password": password,
            **kw,
        }
        r = client.post("/api/members", headers=admin, json=body)
        assert r.status_code == 201, r.text
        m = r.json()
        m["_password"] = password
        return m

    return _m


@pytest.fixture
def member_login(client):
    def _l(member):
        return _login(client, member["mobile"], member["_password"])

    return _l


@pytest.fixture
def subscribe(client, admin):
    def _s(member_id, package_id, start_date=None, **kw):
        body = {"member_id": member_id, "package_id": package_id, **kw}
        if start_date:
            body["start_date"] = start_date
        r = client.post("/api/subscriptions", headers=admin, json=body)
        assert r.status_code == 201, r.text
        return r.json()

    return _s
