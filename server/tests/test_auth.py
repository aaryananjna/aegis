"""Accounts and pairing, against a real TigerDB in a throwaway schema (dropped afterwards).

Skipped when TIGER_DATABASE_URL isn't set (for example in CI).
"""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import asyncpg
import pytest
from fastapi.testclient import TestClient

from aegis_server import db, ratelimit
from aegis_server.ratelimit import Limiter
from aegis_server.routes import auth as auth_routes
from aegis_server.config import settings
from aegis_server.main import app
from aegis_server.security import token_hash

pytestmark = pytest.mark.skipif(not settings.tiger_database_url,
                                reason="TIGER_DATABASE_URL not set")

SCHEMA_SQL = (Path(__file__).resolve().parent.parent / "migrations" / "001_init.sql").read_text()
PW = "correct horse battery"


async def _run(sql: str, schema: str | None = None) -> None:
    conn = await asyncpg.connect(settings.tiger_database_url, timeout=15)
    try:
        if schema:
            await conn.execute(f"SET search_path TO {schema}, public")
        await conn.execute(sql)
    finally:
        await conn.close()


@pytest.fixture(scope="module")
def schema():
    name = f"test_auth_{uuid.uuid4().hex[:10]}"
    asyncio.run(_run(f"CREATE SCHEMA {name}"))
    try:
        asyncio.run(_run(SCHEMA_SQL, name))
        yield name
    finally:
        asyncio.run(_run(f"DROP SCHEMA {name} CASCADE"))


@pytest.fixture(autouse=True)
def _fresh_limits():
    ratelimit.clear_all()
    yield
    ratelimit.clear_all()


@pytest.fixture
def client(schema):
    app.state.db_server_settings = {"search_path": f"{schema}, public"}
    try:
        with TestClient(app) as c:
            yield c
    finally:
        del app.state.db_server_settings


def _email() -> str:
    return f"t{uuid.uuid4().hex[:8]}@example.com"


def _signup(c: TestClient, email: str | None = None, name: str = "Sam Test") -> dict:
    r = c.post("/auth/signup", json={"email": email or _email(), "password": PW,
                                     "display_name": name})
    assert r.status_code == 201, r.text
    return r.json()["user"]


# --- signup / login / logout -------------------------------------------------------------

def test_signup_logs_you_in(client):
    user = _signup(client)
    assert "password" not in str(user) and "hash" not in str(user)
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json() == {"user": user, "elders": []}


def test_password_stored_only_as_argon2(client, schema):
    email = _email()
    _signup(client, email)

    async def get():
        conn = await asyncpg.connect(settings.tiger_database_url, timeout=15)
        try:
            return await conn.fetchval(f"SELECT password_hash FROM {schema}.users WHERE email=$1",
                                       email)
        finally:
            await conn.close()
    stored = asyncio.run(get())
    assert stored.startswith("$argon2id$") and PW not in stored


def test_duplicate_email_is_409_case_insensitive(client):
    email = _email()
    _signup(client, email)
    r = client.post("/auth/signup", json={"email": email.upper(), "password": PW,
                                          "display_name": "Other"})
    assert r.status_code == 409


@pytest.mark.parametrize("body", [
    {"email": "not-an-email", "password": PW, "display_name": "A"},
    {"email": "a@example.com", "password": "short", "display_name": "A"},
    {"email": "a@example.com", "password": PW, "display_name": "   "},
    {"email": "a@example.com", "password": PW},
])
def test_signup_rejects_bad_input(client, body):
    assert client.post("/auth/signup", json=body).status_code == 422


def test_login_and_logout(client):
    email = _email()
    _signup(client, email)
    client.cookies.clear()
    assert client.get("/auth/me").status_code == 401

    r = client.post("/auth/login", json={"email": email.title(), "password": PW})
    assert r.status_code == 200
    assert r.json()["user"]["email"] == email
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert client.get("/auth/me").status_code == 200

    assert client.post("/auth/logout").status_code == 204
    client.cookies.clear()
    assert client.get("/auth/me").status_code == 401


def test_logout_kills_the_token_server_side(client):
    email = _email()
    _signup(client, email)
    token = client.cookies.get("aegis_login")
    client.post("/auth/logout")
    client.cookies.clear()
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_wrong_password_and_unknown_email_look_the_same(client):
    email = _email()
    _signup(client, email)
    client.cookies.clear()
    a = client.post("/auth/login", json={"email": email, "password": "wrong password"})
    b = client.post("/auth/login", json={"email": _email(), "password": PW})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_bearer_token_works(client):
    _signup(client)
    token = client.cookies.get("aegis_login")
    client.cookies.clear()
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert client.get("/auth/me", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_expired_login_is_rejected(client, schema):
    _signup(client)
    token = client.cookies.get("aegis_login")
    asyncio.run(_run(f"UPDATE {schema}.login_sessions SET expires_at = now() - interval '1 s' "
                     f"WHERE token_hash = '\\x{token_hash(token).hex()}'"))
    assert client.get("/auth/me").status_code == 401


# --- grandparents, members, pairing ------------------------------------------------------

def _elder(c: TestClient, name: str = "Grandma Test") -> dict:
    r = c.post("/elders", json={"display_name": name})
    assert r.status_code == 201, r.text
    return r.json()["elder"]


def test_create_elder_needs_login(client):
    client.cookies.clear()
    assert client.post("/elders", json={"display_name": "X"}).status_code == 401


def test_owner_creates_elder_and_sees_it(client):
    _signup(client)
    elder = _elder(client)
    elders = client.get("/auth/me").json()["elders"]
    assert elders == [{**elder, "role": "owner"}]


def test_pair_device_and_device_me(client):
    _signup(client)
    elder = _elder(client)
    r = client.post(f"/elders/{elder['id']}/devices")
    assert r.status_code == 201
    token = r.json()["device_token"]
    assert r.json()["pair_url"].endswith(f"/pair#{token}")

    client.cookies.clear()  # the grandparent's laptop has no login
    got = client.get("/device/me", headers={"X-Device-Token": token})
    assert got.status_code == 200 and got.json() == {"elder": elder}
    assert client.get("/device/me").status_code == 401
    assert client.get("/device/me", headers={"X-Device-Token": "nope"}).status_code == 401


def test_unpair_device(client):
    _signup(client)
    elder = _elder(client)
    token = client.post(f"/elders/{elder['id']}/devices").json()["device_token"]
    assert client.delete(f"/elders/{elder['id']}/devices").status_code == 204
    assert client.get("/device/me", headers={"X-Device-Token": token}).status_code == 401


def test_add_viewer_and_viewer_limits(client):
    viewer_email = _email()
    _signup(client, viewer_email, "Jo Test")
    viewer_cookie = client.cookies.get("aegis_login")

    client.cookies.clear()
    _signup(client)
    elder = _elder(client)
    r = client.post(f"/elders/{elder['id']}/members", json={"email": viewer_email})
    assert r.status_code == 201 and r.json()["member"]["role"] == "viewer"
    assert client.post(f"/elders/{elder['id']}/members",
                       json={"email": viewer_email}).status_code == 409
    assert client.post(f"/elders/{elder['id']}/members",
                       json={"email": _email()}).status_code == 404

    client.cookies.clear()
    v = {"Authorization": f"Bearer {viewer_cookie}"}
    assert client.get("/auth/me", headers=v).json()["elders"] == [{**elder, "role": "viewer"}]
    assert client.post(f"/elders/{elder['id']}/devices", headers=v).status_code == 403


def test_strangers_get_404_not_403(client):
    _signup(client)
    elder = _elder(client)
    client.cookies.clear()
    _signup(client)  # someone else
    assert client.post(f"/elders/{elder['id']}/devices").status_code == 404
    assert client.post(f"/elders/{uuid.uuid4()}/devices").status_code == 404


def test_no_database_means_503():
    assert db._pool is None  # each client above closed its pool on exit
    c = TestClient(app)  # no `with`, so no startup and no pool
    assert c.post("/auth/login", json={"email": "a@b.co", "password": "x"}).status_code == 503
    assert c.get("/auth/me", headers={"Authorization": "Bearer x"}).status_code == 503


# --- hardening -----------------------------------------------------------------------------

def test_hashing_runs_off_the_event_loop(client, monkeypatch):
    seen = []
    real = asyncio.to_thread

    async def spy(fn, *a, **kw):
        seen.append(fn.__name__)
        return await real(fn, *a, **kw)
    monkeypatch.setattr(auth_routes.asyncio, "to_thread", spy)
    email = _email()
    _signup(client, email)
    client.post("/auth/login", json={"email": email, "password": PW})
    assert seen == ["hash_password", "verify_password"]


def test_failed_logins_per_email_get_429(client):
    email = _email()
    _signup(client, email)
    client.cookies.clear()
    for _ in range(5):
        assert client.post("/auth/login",
                           json={"email": email, "password": "wrong pw!"}).status_code == 401
    r = client.post("/auth/login", json={"email": email.upper(), "password": PW})
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0


def test_good_login_resets_the_email_count(client):
    email = _email()
    _signup(client, email)
    for _ in range(4):
        client.post("/auth/login", json={"email": email, "password": "wrong pw!"})
    assert client.post("/auth/login", json={"email": email, "password": PW}).status_code == 200
    for _ in range(4):
        assert client.post("/auth/login",
                           json={"email": email, "password": "wrong pw!"}).status_code == 401


def test_failed_logins_per_address_get_429(client):
    for _ in range(20):
        client.post("/auth/login", json={"email": _email(), "password": "wrong pw!"})
    r = client.post("/auth/login", json={"email": _email(), "password": PW})
    assert r.status_code == 429


def test_signups_per_address_get_429(client):
    for _ in range(10):
        _signup(client)
    r = client.post("/auth/signup", json={"email": _email(), "password": PW,
                                          "display_name": "Too Many"})
    assert r.status_code == 429


def test_limiter_window_slides():
    lim = Limiter(limit=2, window_s=10)
    lim.hit("k", now=0)
    lim.hit("k", now=1)
    assert lim.retry_after("k", now=5) == 5
    assert lim.retry_after("k", now=10.5) == 0
    assert lim.retry_after("other", now=5) == 0
