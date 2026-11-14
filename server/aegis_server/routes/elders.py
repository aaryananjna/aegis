"""Grandparents and their paired laptops (option D).

A family member creates the grandparent, then pairs the grandparent's laptop once. The laptop
keeps the device token it gets back and sends it as `X-Device-Token`; the grandparent never logs in.

POST   /elders                      {display_name}  -> 201 {elder}     (you become owner)
POST   /elders/{elder_id}/members   {email}         -> 201 {member}    (owner only; adds a viewer)
POST   /elders/{elder_id}/devices                   -> 201 {device_token, pair_url}  (owner only)
DELETE /elders/{elder_id}/devices                   -> 204             (owner only; unpairs all)
GET    /device/me                                   -> 200 {elder}     (X-Device-Token)

The device token is shown exactly once, in the POST response. Only its sha256 is stored.
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from .. import db
from ..config import settings
from ..security import new_token, token_hash
from .auth import CurrentUser, User

router = APIRouter(tags=["elders"])


class ElderIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)


class MemberIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class Elder(BaseModel):
    id: UUID
    display_name: str


async def _role(elder_id: UUID, user: User) -> str | None:
    return await db.pool().fetchval(
        "SELECT role FROM elder_members WHERE elder_id = $1 AND user_id = $2", elder_id, user.id)


async def _require_owner(elder_id: UUID, user: User) -> None:
    role = await _role(elder_id, user)
    if role is None:
        # Same answer as "doesn't exist", so ids of other families' grandparents don't leak.
        raise HTTPException(status_code=404, detail="no such grandparent")
    if role != "owner":
        raise HTTPException(status_code=403, detail="only the owner can do this")


@router.post("/elders", status_code=201)
async def create_elder(body: ElderIn, user: CurrentUser) -> dict:
    name = body.display_name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="display_name is empty")
    async with db.pool().acquire() as conn, conn.transaction():
        row = await conn.fetchrow(
            "INSERT INTO elders (display_name) VALUES ($1) RETURNING id, display_name", name)
        await conn.execute(
            "INSERT INTO elder_members (elder_id, user_id, role) VALUES ($1, $2, 'owner')",
            row["id"], user.id)
    return {"elder": Elder(id=row["id"], display_name=row["display_name"])}


@router.post("/elders/{elder_id}/members", status_code=201)
async def add_member(elder_id: UUID, body: MemberIn, user: CurrentUser) -> dict:
    await _require_owner(elder_id, user)
    pool = db.pool()
    other = await pool.fetchrow("SELECT id, display_name FROM users WHERE email = $1",
                                body.email.strip())
    if other is None:
        raise HTTPException(status_code=404, detail="that person needs to sign up first")
    try:
        await pool.execute(
            "INSERT INTO elder_members (elder_id, user_id, role) VALUES ($1, $2, 'viewer')",
            elder_id, other["id"])
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=409, detail="already watching this grandparent")
    return {"member": {"user_id": other["id"], "display_name": other["display_name"],
                       "role": "viewer"}}


@router.post("/elders/{elder_id}/devices", status_code=201)
async def pair_device(elder_id: UUID, user: CurrentUser) -> dict:
    await _require_owner(elder_id, user)
    token = new_token()
    await db.pool().execute("INSERT INTO elder_devices (token_hash, elder_id) VALUES ($1, $2)",
                            token_hash(token), elder_id)
    # The token goes after '#', so it never reaches a server log or a Referer header.
    return {"device_token": token, "pair_url": f"{settings.web_base_url}/pair#{token}"}


@router.delete("/elders/{elder_id}/devices", status_code=204)
async def unpair_devices(elder_id: UUID, user: CurrentUser) -> None:
    await _require_owner(elder_id, user)
    await db.pool().execute("DELETE FROM elder_devices WHERE elder_id = $1", elder_id)


async def current_elder(x_device_token: Annotated[str | None, Header()] = None) -> Elder:
    """Dependency: the grandparent whose paired laptop sent this request, or 401."""
    if not x_device_token:
        raise HTTPException(status_code=401, detail="device not paired")
    row = await db.pool().fetchrow(
        "UPDATE elder_devices d SET last_seen = now() FROM elders e "
        "WHERE d.token_hash = $1 AND e.id = d.elder_id RETURNING e.id, e.display_name",
        token_hash(x_device_token))
    if row is None:
        raise HTTPException(status_code=401, detail="device not paired")
    return Elder(id=row["id"], display_name=row["display_name"])


CurrentElder = Annotated[Elder, Depends(current_elder)]


@router.get("/device/me")
async def device_me(elder: CurrentElder) -> dict:
    return {"elder": elder}
