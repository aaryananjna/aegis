"""HTTP endpoints for starting and ending calls. All but /health are laptop only.

POST /sessions            {name?, phone?, mic?, device?} -> {session_id, elder_url, family_url}
POST /sessions/{id}/end                                  -> {ok}
POST /typed               {session_id, text, speaker_raw?} -> {ok, utterance_id}
GET  /health                                             -> {ok, ...}

`mic: true` starts live captions from the laptop mic inside the server (Deepgram) for this
call; they stop when the call ends. Without it, captions come in on WS /captions or /typed.
"""
from __future__ import annotations

import os
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request, Response
from hangup_detect import make_segment
from pydantic import BaseModel, Field

from .. import db
from ..config import settings
from ..netguard import is_laptop
from ..roles import ROLES
from ..sessions import TooManySessions, store

router = APIRouter()


def require_laptop(request: Request) -> None:
    if not is_laptop(request):
        raise HTTPException(status_code=403, detail="only from the laptop itself")


class NewSession(BaseModel):
    name: str | None = Field(default=None, max_length=40)    # display only, made up in demos
    phone: str | None = Field(default=None, max_length=20, pattern=r"^\+?[0-9 ()-]{3,20}$")
    mic: bool = False                                        # live captions from the laptop mic
    device: str | None = Field(default=None, max_length=80)  # mic number or name


class Typed(BaseModel):
    session_id: str = Field(max_length=64)
    text: str = Field(max_length=2000)
    speaker_raw: str | None = Field(default="1", max_length=64)  # the caller in the demo


@router.get("/health")
async def health() -> dict:
    return {"ok": True, "server": "aegis", "sessions": len(store),
            "stt": bool(settings.deepgram_api_key),
            "ai_layer": bool(os.environ.get("GROQ_API_KEY") or os.environ.get("GEMINI_API_KEY")),
            "accounts_db": db.is_open()}


@router.post("/sessions")
async def create_session(request: Request, response: Response,
                         body: NewSession | None = None) -> dict:
    require_laptop(request)
    body = body or NewSession()
    if body.mic and not settings.deepgram_api_key:
        raise HTTPException(status_code=400, detail="DEEPGRAM_API_KEY is not set")
    try:
        s = store.create()
    except TooManySessions:
        raise HTTPException(status_code=429, detail="too many calls at once; end one first")
    if body.mic:
        device = int(body.device) if body.device and body.device.isdigit() else body.device
        s.start_mic(device)
    extra = {k: v for k, v in (("name", body.name), ("phone", body.phone)) if v}
    urls = {role: f"{settings.web_base_url}/{role}?" + urlencode(
        {"session": s.session_id, "token": s.tokens[role], **(extra if role == "family" else {})})
        for role in ROLES}
    # Printed to the laptop's own terminal only (the server's logs never hold tokens).
    print(f"\n  Aegis call {s.session_id}{' (live mic)' if body.mic else ''}\n"
          f"  elder:  {urls['elder']}\n  family: {urls['family']}\n", flush=True)
    return {"session_id": s.session_id, "elder_url": urls["elder"],
            "family_url": urls["family"]}


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str, request: Request) -> dict:
    require_laptop(request)
    s = store.get(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="no such call")
    await s.put(("end", None))
    return {"ok": True}


@router.post("/typed")
async def typed(body: Typed, request: Request) -> dict:
    """Noisy-hall fallback: a typed line becomes a final caption with source "typed"."""
    require_laptop(request)
    s = store.get(body.session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="no such call")
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="text is empty")
    s.typed_count += 1
    now = s.now()
    seg = make_segment(f"typed-{s.typed_count}", 0, "unknown", text, now, now, True,
                       speaker_raw=body.speaker_raw)
    await s.put(("caption", (seg, "typed")))
    return {"ok": True, "utterance_id": seg.utterance_id}
