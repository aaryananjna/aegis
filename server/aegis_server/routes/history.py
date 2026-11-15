"""Call history for the family dashboard (#44). Logged-in family only; numbers only.

GET /elders/{elder_id}/live
    -> {"live": null} or {"live": {session_id, family_token, started_at}}
       The grandparent's call happening right now, for the family dashboard on the phone: it
       checks every few seconds and connects to /events?role=family with this token.
GET /elders/{elder_id}/calls?limit=20
    -> {"calls": [{id, started_at, ended_at, max_score, max_level, flagged_at, card}]}, newest first
GET /elders/{elder_id}/calls/{call_id}/risk?bucket=1
    -> {"call": {...}, "points": [{t, time, score, max, level}]}
       One point per `bucket` seconds (Timescale time_bucket), t = seconds since the call started.

Any member (owner or viewer) can read. Someone who doesn't watch that grandparent gets 404,
same as a grandparent that doesn't exist. Under /elders so it goes through the web proxy.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from datetime import datetime, timezone

from .. import db
from ..sessions import store
from .auth import CurrentUser, User

router = APIRouter(tags=["history"])

CALL_COLUMNS = "id, started_at, ended_at, max_score, max_level, flagged_at, card"


async def _require_member(elder_id: UUID, user: User) -> None:
    ok = await db.pool().fetchval(
        "SELECT 1 FROM elder_members WHERE elder_id = $1 AND user_id = $2", elder_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="no such grandparent")


def _call(r) -> dict:
    ms = r["max_score"]
    return {"id": r["id"], "started_at": r["started_at"], "ended_at": r["ended_at"],
            "max_score": None if ms is None else round(ms, 4), "max_level": r["max_level"],
            "flagged_at": r["flagged_at"], "card": r["card"]}


@router.get("/elders/{elder_id}/live")
async def live_call(elder_id: UUID, user: CurrentUser) -> dict:
    """Logged-in family only (owner or viewer). Hands out the call's family token, which only
    opens the read-only family view and dies when the call ends."""
    await _require_member(elder_id, user)
    s = store.live_for(elder_id)
    if s is None:
        return {"live": None}
    return {"live": {"session_id": s.session_id, "family_token": s.tokens["family"],
                     "started_at": datetime.fromtimestamp(s.started_at, timezone.utc)}}


@router.get("/elders/{elder_id}/calls")
async def list_calls(elder_id: UUID, user: CurrentUser,
                     limit: int = Query(default=20, ge=1, le=100)) -> dict:
    await _require_member(elder_id, user)
    rows = await db.pool().fetch(
        f"SELECT {CALL_COLUMNS} FROM calls WHERE elder_id = $1 "
        "ORDER BY started_at DESC LIMIT $2", elder_id, limit)
    return {"calls": [_call(r) for r in rows]}


@router.get("/elders/{elder_id}/calls/{call_id}/risk")
async def call_risk(elder_id: UUID, call_id: str, user: CurrentUser,
                    bucket: int = Query(default=1, ge=1, le=300)) -> dict:
    await _require_member(elder_id, user)
    pool = db.pool()
    call = await pool.fetchrow(
        f"SELECT {CALL_COLUMNS} FROM calls WHERE id = $1 AND elder_id = $2", call_id[:64],
        elder_id)
    if call is None:
        raise HTTPException(status_code=404, detail="no such call")
    rows = await pool.fetch(
        "SELECT time_bucket(make_interval(secs => $2), time) AS b, avg(score) AS score, "
        "max(score) AS max, last(level, time) AS level "
        "FROM risk_points WHERE call_id = $1 GROUP BY b ORDER BY b", call_id, bucket)
    start = call["started_at"]
    return {"call": _call(call),
            "points": [{"t": max(0.0, round((r["b"] - start).total_seconds(), 1)), "time": r["b"],
                        "score": round(r["score"], 4), "max": round(r["max"], 4),
                        "level": r["level"]} for r in rows]}
