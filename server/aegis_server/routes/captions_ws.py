"""WS /captions/{session_id}: captions in, nothing out (CONTRACTS v2.1, C3, C14).

Used by the separate-process Deepgram client, type mode and tests. It has no token, so it only
accepts the laptop itself: loopback and no forwarding headers (see netguard). Inbound: caption,
set_elder, end. Messages over 16 KB, or not JSON, are dropped.
"""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..messages import CAPTIONS_INBOUND, decode, parse
from ..netguard import is_laptop
from ..sessions import store

router = APIRouter()

POLICY_VIOLATION = 1008
BAD_TOKEN = 4401


@router.websocket("/captions/{session_id}")
async def captions(ws: WebSocket, session_id: str) -> None:
    # Accept, then close with the contract's code: a refused handshake only shows as 1006.
    # Nothing is read from a refused socket.
    await ws.accept()
    if not is_laptop(ws):
        await ws.close(code=POLICY_VIOLATION)
        return
    s = store.get(session_id)
    if s is None or s.ended:
        await ws.close(code=BAD_TOKEN)
        return
    try:
        while not s.ended:
            item = parse(decode(await ws.receive_text()), CAPTIONS_INBOUND)
            if item is not None:
                await s.put(item)
    except WebSocketDisconnect:
        pass
    except Exception:  # binary frame or a closed session: just hang up
        pass
