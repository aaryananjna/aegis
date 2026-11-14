"""Family accounts stored in TigerDB (option D: family members log in; the grandparent never does).

POST /auth/signup   {email, password, display_name}  -> 201 {user}, sets the login cookie
POST /auth/login    {email, password}                -> 200 {user}, sets the login cookie
POST /auth/logout                                     -> 204, ends this login
GET  /auth/me                                         -> 200 {user, elders}

The login token travels in an httpOnly cookie (`aegis_login`). Scripts and tests may send it as
`Authorization: Bearer <token>` instead. Only its sha256 is stored.

Password hashing runs in a worker thread so it never stalls live calls on the event loop.
Failed logins are limited per email (5 per 15 min) and per client address (20 per 15 min);
signups per client address (10 per hour). Over the limit: 429 with Retry-After. Logging in sits alongside the
per-call family link from CONTRACTS.md; it doesn't replace it.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

from .. import db, ratelimit
from ..config import settings
from ..security import hash_password, new_token, token_hash, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE = "aegis_login"


class SignupIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=256)
    display_name: str = Field(min_length=1, max_length=80)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip()
        local, _, domain = v.partition("@")
        if not local or "." not in domain or " " in v:
            raise ValueError("not an email address")
        return v

    @field_validator("display_name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("display_name is empty")
        return v


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)


class User(BaseModel):
    id: UUID
    email: str
    display_name: str


def _user(row: asyncpg.Record) -> User:
    return User(id=row["id"], email=row["email"], display_name=row["display_name"])


async def _start_login(conn: asyncpg.Connection, response: Response, user_id: UUID) -> None:
    token = new_token()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.login_days)
    await conn.execute(
        "INSERT INTO login_sessions (token_hash, user_id, expires_at) VALUES ($1, $2, $3)",
        token_hash(token), user_id, expires)
    response.set_cookie(COOKIE, token, max_age=settings.login_days * 86400, httponly=True,
                        samesite="lax", secure=settings.cookie_secure, path="/")


def _client(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _check(limiter: ratelimit.Limiter, key: str) -> None:
    wait = limiter.retry_after(key)
    if wait:
        raise HTTPException(status_code=429, detail="too many attempts, try again later",
                            headers={"Retry-After": str(wait)})


def _token_from(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return request.cookies.get(COOKIE)


async def current_user(request: Request) -> User:
    """Dependency: the logged-in family member, or 401."""
    token = _token_from(request)
    if not token:
        raise HTTPException(status_code=401, detail="not logged in")
    row = await db.pool().fetchrow(
        "SELECT u.id, u.email, u.display_name FROM login_sessions s "
        "JOIN users u ON u.id = s.user_id WHERE s.token_hash = $1 AND s.expires_at > now()",
        token_hash(token))
    if row is None:
        raise HTTPException(status_code=401, detail="not logged in")
    return _user(row)


CurrentUser = Annotated[User, Depends(current_user)]


@router.post("/signup", status_code=201)
async def signup(body: SignupIn, request: Request, response: Response) -> dict:
    ip = _client(request)
    _check(ratelimit.signup_by_ip, ip)
    ratelimit.signup_by_ip.hit(ip)
    pw_hash = await asyncio.to_thread(hash_password, body.password)
    async with db.pool().acquire() as conn, conn.transaction():
        try:
            row = await conn.fetchrow(
                "INSERT INTO users (email, password_hash, display_name) VALUES ($1, $2, $3) "
                "RETURNING id, email, display_name", body.email, pw_hash, body.display_name)
        except asyncpg.UniqueViolationError:
            raise HTTPException(status_code=409, detail="an account with that email exists")
        await _start_login(conn, response, row["id"])
    return {"user": _user(row)}


@router.post("/login")
async def login(body: LoginIn, request: Request, response: Response) -> dict:
    email, ip = body.email.strip().lower(), _client(request)
    _check(ratelimit.login_by_email, email)
    _check(ratelimit.login_by_ip, ip)
    async with db.pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, display_name, password_hash FROM users WHERE email = $1", email)
        # Always run one verify, so an unknown email and a wrong password look the same.
        ok = await asyncio.to_thread(verify_password,
                                     row["password_hash"] if row else None, body.password)
        if not ok:
            ratelimit.login_by_email.hit(email)
            ratelimit.login_by_ip.hit(ip)
            raise HTTPException(status_code=401, detail="wrong email or password")
        ratelimit.login_by_email.reset(email)
        await conn.execute("DELETE FROM login_sessions WHERE user_id = $1 AND expires_at <= now()",
                           row["id"])
        await _start_login(conn, response, row["id"])
    return {"user": _user(row)}


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response) -> None:
    token = _token_from(request)
    if token:
        await db.pool().execute("DELETE FROM login_sessions WHERE token_hash = $1",
                                token_hash(token))
    response.delete_cookie(COOKIE, path="/", samesite="lax", secure=settings.cookie_secure,
                           httponly=True)


@router.get("/me")
async def me(user: CurrentUser) -> dict:
    rows = await db.pool().fetch(
        "SELECT e.id, e.display_name, m.role FROM elder_members m "
        "JOIN elders e ON e.id = m.elder_id WHERE m.user_id = $1 ORDER BY e.created_at",
        user.id)
    return {"user": user,
            "elders": [{"id": r["id"], "display_name": r["display_name"], "role": r["role"]}
                       for r in rows]}
