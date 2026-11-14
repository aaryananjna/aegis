"""WS /events/{session_id}?role=elder|family&token=…: events out (CONTRACTS v2.1, C3/C4/C6).

- A wrong or expired token, a token for the other role, or an unknown call all close with 4401
  (the same answer, so nothing leaks about which part was wrong).
- On connect: replay that role's past events, then live events.
- role=elder may send set_elder and codeword_result. role=family inbound is read (so a closed
  phone is noticed) and ignored.
- Inbound is limited: messages over 16 KB are dropped, and more than 20 messages in a second
  closes the socket (1008).
"""
from __future__ import annotations

import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..messages import ELDER_INBOUND, decode, parse
from ..roles import ROLES
from ..sessions import store

router = APIRouter()

BAD_TOKEN = 4401
POLICY_VIOLATION = 1008
MAX_PER_SECOND = 20


@router.websocket("/events/{session_id}")
async def events(ws: WebSocket, session_id: str, role: str = "", token: str = "") -> None:
    # Accept, then close with 4401: a refused handshake only shows as 1006 in the browser,
    # and the screens need 4401 to say "this link has expired". Nothing is sent or read first.
    await ws.accept()
    s = store.get(session_id)
    if role not in ROLES or s is None or not s.check_token(role, token):
        await ws.close(code=BAD_TOKEN)
        return
    lis = s.join(ws, role)
    window, count = time.monotonic(), 0
    try:
        while not lis.closed:
            raw = await ws.receive_text()
            now = time.monotonic()
            if now - window >= 1.0:
                window, count = now, 0
            count += 1
            if count > MAX_PER_SECOND:
                await ws.close(code=POLICY_VIOLATION)
                break
            if role == "elder":
                item = parse(decode(raw), ELDER_INBOUND)
                if item is not None:
                    await s.put(item)
    except WebSocketDisconnect:
        pass
    except Exception:  # binary frame, or the socket closed under us
        pass
    finally:
        lis.close()
