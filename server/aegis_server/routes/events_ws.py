"""WS /events/{session_id}?role=elder|family&token=…: events out (CONTRACTS v2.1, C3/C4/C6).

- A wrong or expired token, or a token for the other role, closes with code 4401.
- On connect: replay that role's past events, then live events.
- role=elder may send set_elder and codeword_result. role=family inbound is ignored.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, WebSocket

router = APIRouter()

BAD_TOKEN = 4401


@router.websocket("/events/{session_id}")
async def events(ws: WebSocket, session_id: str,
                 role: str = Query(...), token: str = Query(...)) -> None:
    # TODO: check role and token (close 4401 if wrong), accept, register the listener,
    # replay history for the role, then read inbound messages (elder only) until disconnect.
    await ws.close(code=BAD_TOKEN, reason="not implemented yet")
