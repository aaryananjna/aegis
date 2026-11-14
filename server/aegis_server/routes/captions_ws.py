"""WS /captions/{session_id}: captions in, nothing out (CONTRACTS v2.1, C3).

Used by A's own STT, type mode and tests. It has no token, so it only accepts connections
from the laptop itself (localhost); anything else on the hotspot is refused.
Inbound: caption, set_elder, end.
"""
from __future__ import annotations

from fastapi import APIRouter, WebSocket

router = APIRouter()

POLICY_VIOLATION = 1008


@router.websocket("/captions/{session_id}")
async def captions(ws: WebSocket, session_id: str) -> None:
    # TODO: refuse non-localhost clients, look up the session, then parse each message
    # with messages.parse(msg, CAPTIONS_INBOUND) and put it on the session queue.
    await ws.close(code=POLICY_VIOLATION, reason="not implemented yet")
