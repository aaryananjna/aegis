"""Call history in TigerDB: one `calls` row per call and the risk score once a second.

Numbers only: score, level, which card showed, when. Never caption text, quotes or audio.
Only calls started from a paired laptop are recorded (they know which grandparent it is).

A database problem must never touch a live call: every write is wrapped, logged without
details, and dropped. Risk points are buffered and written in batches every few seconds.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from . import db

log = logging.getLogger("aegis.history")

FLUSH_S = 3.0
LEVEL_RANK = {"low": 0, "elevated": 1, "high": 2}
_FINISHING: set[asyncio.Task] = set()  # finish() outlives the session that started it


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CallRecorder:
    def __init__(self, call_id: str, elder_id: UUID) -> None:
        self.call_id = call_id
        self.elder_id = elder_id
        self.started_at = _now()
        self.score = 0.0
        self.level = "low"
        self.max_score = 0.0
        self.max_level = "low"
        self.flagged_at: datetime | None = None
        self.card: str | None = None
        self._points: list[tuple[datetime, str, float, str]] = []
        self._ready = asyncio.Event()
        self._ok = True
        self._flusher = asyncio.create_task(self._run())

    # ---- called by the session owner (never awaits, never raises) -------------------------

    def observe(self, events: list[dict]) -> None:
        for e in events:
            kind = e.get("type")
            if kind == "risk":
                self.score = float(e.get("score", 0.0))
                self.level = e.get("level", self.level)
                self.max_score = max(self.max_score, self.score)
                if LEVEL_RANK.get(self.level, 0) > LEVEL_RANK.get(self.max_level, 0):
                    self.max_level = self.level
                if self.level == "high" and self.flagged_at is None:
                    self.flagged_at = _now()
            elif kind == "intervention" and e.get("kind") in ("codeword", "verify", "hangup"):
                self.card = e["kind"]  # the latest card wins (hangup after codeword)

    def sample(self) -> None:
        """One point per second, from the last risk the detector sent."""
        if self._ok:
            self._points.append((_now(), self.call_id, round(self.score, 4), self.level))

    def finish(self) -> None:
        self._flusher.cancel()
        t = asyncio.create_task(self._finish())
        _FINISHING.add(t)
        t.add_done_callback(_FINISHING.discard)

    # ---- database side --------------------------------------------------------------------

    async def _run(self) -> None:
        try:
            await db.pool().execute(
                "INSERT INTO calls (id, elder_id, started_at) VALUES ($1, $2, $3)",
                self.call_id, self.elder_id, self.started_at)
            self._ready.set()
            while True:
                await asyncio.sleep(FLUSH_S)
                await self._flush()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self._ok = False
            self._points.clear()
            log.warning("call %s: history off for this call (%s)", self.call_id, type(e).__name__)

    async def _flush(self) -> None:
        if not self._points or not self._ready.is_set():
            return
        batch, self._points = self._points, []
        await db.pool().executemany(
            "INSERT INTO risk_points (time, call_id, score, level) VALUES ($1, $2, $3, $4)", batch)

    async def _finish(self) -> None:
        try:
            if not self._ready.is_set():
                return  # the calls row never got written
            await self._flush()
            await db.pool().execute(
                "UPDATE calls SET ended_at = $2, max_score = $3, max_level = $4, flagged_at = $5, "
                "card = $6 WHERE id = $1",
                self.call_id, _now(), round(self.max_score, 4), self.max_level, self.flagged_at,
                self.card)
        except Exception as e:
            log.warning("call %s: couldn't save the end of the call (%s)", self.call_id,
                        type(e).__name__)


async def elder_for_device(token: str) -> UUID | None:
    """The grandparent a paired laptop belongs to, or None."""
    from .security import token_hash
    return await db.pool().fetchval(
        "UPDATE elder_devices SET last_seen = now() WHERE token_hash = $1 RETURNING elder_id",
        token_hash(token))
