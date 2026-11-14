"""One Session per call (CONTRACTS v2.1, "Rules for A's server").

- One owner task is the only code that touches the Detector. Captions, ticks, set_elder,
  codeword_result and end all go through one asyncio.Queue, in order.
- A tick every second, even in silence.
- Two random tokens per session, one per role. They stop working when the session ends.
- Event history for replay on reconnect (C6) lives in memory only and is dropped at the end.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from fastapi import WebSocket


@dataclass
class Listener:
    ws: WebSocket
    role: str  # "elder" or "family"


@dataclass
class Session:
    session_id: str
    tokens: dict[str, str]  # role -> token
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    listeners: set = field(default_factory=set)
    history: list[dict] = field(default_factory=list)  # every outbound event, in order
    ended: bool = False

    def check_token(self, role: str, token: str) -> bool:
        """Constant-time token check for this role; False once the session has ended."""
        raise NotImplementedError

    async def owner(self) -> None:
        """The only task that touches the detector. Forwards captions to elder listeners
        before the detector's events for them (C1), then broadcasts everything."""
        raise NotImplementedError

    async def ticker(self) -> None:
        """Queue a tick every settings.tick_s seconds until the session ends."""
        raise NotImplementedError

    async def broadcast(self, events: list[dict]) -> None:
        """Record events in history and send each to listeners whose role allows it."""
        raise NotImplementedError

    async def replay(self, listener: Listener) -> None:
        """Send this role's past events, in order, to a listener that just (re)connected."""
        raise NotImplementedError

    async def end(self) -> None:
        """Run Detector.end, send call_ended to everyone, expire tokens, drop history."""
        raise NotImplementedError


class SessionStore:
    """All live sessions, in memory only."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self) -> Session:
        raise NotImplementedError

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)


store = SessionStore()
