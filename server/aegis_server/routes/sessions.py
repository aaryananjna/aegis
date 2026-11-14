"""HTTP endpoints for starting and ending calls."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"ok": True}


@router.post("/sessions")
async def create_session() -> dict:
    """Start a call. Returns session_id plus the elder and family links (with tokens).

    Response: {"session_id": ..., "elder_url": ..., "family_url": ...}
    The server also prints both links in the terminal.
    """
    raise HTTPException(status_code=501, detail="not implemented yet")


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str) -> dict:
    """End a call from the laptop (same as an `end` message on /captions)."""
    raise HTTPException(status_code=501, detail="not implemented yet")
