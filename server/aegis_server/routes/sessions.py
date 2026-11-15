"""HTTP endpoints for starting and ending calls. All but /health are laptop only.

POST /sessions            {name?, phone?, mic?, device?} -> {session_id, elder_url, family_url}
POST /sessions/start      form or JSON from the website   -> 303 to the elder screen
POST /sessions/{id}/end                                  -> {ok}
POST /typed               {session_id, text, speaker_raw?} -> {ok, utterance_id}
GET  /health                                             -> {ok, ...}

`mic: true` starts live captions from the laptop mic inside the server (Deepgram) for this
call; they stop when the call ends. `labels: false` turns off speaker labels: every line is
scored from the start, no tap and no voice guess. Without it, captions come in on WS /captions or /typed.
"""
from __future__ import annotations

import os
import json
from urllib.parse import parse_qs, quote, urlencode

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from hangup_detect import make_segment
from pydantic import BaseModel, Field

from .. import db
from ..config import settings
from ..history import elder_for_device
from ..netguard import is_laptop
from ..roles import ROLES
from ..sessions import AI_ANSWERS, TooManySessions, store

router = APIRouter()


def require_laptop(request: Request) -> None:
    if not is_laptop(request):
        raise HTTPException(status_code=403, detail="only from the laptop itself")


class NewSession(BaseModel):
    name: str | None = Field(default=None, max_length=40)    # display only, made up in demos
    phone: str | None = Field(default=None, max_length=20, pattern=r"^\+?[0-9 ()-]{3,20}$")
    mic: bool = False                                        # live captions from the laptop mic
    device: str | None = Field(default=None, max_length=80)  # mic number or name
    # False: no speaker labels from Deepgram; every line is scored. For one laptop mic that
    # hears both the phone speaker and the grandparent, where labels drift between voices.
    labels: bool = True
    # Staged test calls only: save the final lines as a local .call file for B's eval.
    save_transcript: bool = False


class Typed(BaseModel):
    session_id: str = Field(max_length=64)
    text: str = Field(max_length=2000)
    speaker_raw: str | None = Field(default="1", max_length=64)  # the caller in the demo


@router.get("/health")
async def health() -> dict:
    return {"ok": True, "server": "aegis", "sessions": len(store),
            "stt": bool(settings.deepgram_api_key),
            "ai_layer": bool(os.environ.get("GROQ_API_KEY") or os.environ.get("GEMINI_API_KEY")),
            "ai_answers": dict(AI_ANSWERS),
            "accounts_db": db.is_open()}


@router.post("/sessions")
async def create_session(request: Request, response: Response,
                         body: NewSession | None = None,
                         x_device_token: Annotated[str | None, Header()] = None) -> dict:
    require_laptop(request)
    return await _start_call(body or NewSession(), x_device_token)


async def _start_call(body: NewSession, x_device_token: str | None) -> dict:
    """Start a call: tokens, mic, history. Shared by POST /sessions and /sessions/start."""
    device = None
    if body.mic:
        if not settings.deepgram_api_key:
            raise HTTPException(status_code=400, detail="DEEPGRAM_API_KEY is not set")
        from ..stt.deepgram import SttError, check_mic
        device = int(body.device) if body.device and body.device.isdigit() else body.device
        try:
            check_mic(device)  # a missing library or a wrong mic name fails here, not silently
        except SttError as e:
            raise HTTPException(status_code=400, detail=str(e))
        # There's one laptop mic: a new mic call ends any old one (a closed tab or a second
        # start-call would otherwise keep listening and using AI quota).
        for old in store.mic_calls():
            await old.put(("end", None))
    # A paired laptop says which grandparent this is, so the call goes in her history.
    elder_id = None
    if x_device_token and db.is_open():
        try:
            elder_id = await elder_for_device(x_device_token)
            if elder_id is None:
                raise HTTPException(status_code=401, detail="this laptop isn't paired")
        except HTTPException:
            raise
        except Exception:
            elder_id = None  # the database is down: the call still runs, just unrecorded
    try:
        s = store.create(elder_id, save_transcript=body.save_transcript)
    except TooManySessions:
        raise HTTPException(status_code=429, detail="too many calls at once; end one first")
    if body.mic:
        s.start_mic(device, labels=body.labels)
    extra = {k: v for k, v in (("name", body.name), ("phone", body.phone)) if v}
    urls = {role: f"{settings.web_base_url}/{role}?" + urlencode(
        {"session": s.session_id, "token": s.tokens[role], **(extra if role == "family" else {})})
        for role in ROLES}
    # Printed to the laptop's own terminal only (the server's logs never hold tokens).
    print(f"\n  Aegis call {s.session_id}{' (live mic)' if body.mic else ''}"
          f"{' (saved to history)' if s.recorder else ''}\n"
          f"  elder:  {urls['elder']}\n  family: {urls['family']}\n", flush=True)
    return {"session_id": s.session_id, "elder_url": urls["elder"],
            "family_url": urls["family"], "recorded": s.recorder is not None}


def _truthy(v: str | None, default: bool) -> bool:
    if v is None or v == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


@router.post("/sessions/start")
async def start_from_site(request: Request) -> RedirectResponse:
    """The website's "Start a call" button: a plain form POST, answered with a redirect to the
    elder screen. The family link goes after '#family=', so the screen can show it as a QR
    code without it ever reaching a server or a log.

    Demo defaults: live mic, speaker labels off. Form fields (all optional): name, phone,
    mic, labels, device, device_token (the paired laptop's token, for the call history).
    A POST, never a GET: browsers send Origin on form posts, so only our own site gets in.
    """
    require_laptop(request)
    # Browsers also say where a request came from; anything cross-site is refused.
    if request.headers.get("sec-fetch-site", "same-origin") not in ("same-origin", "none"):
        raise HTTPException(status_code=403, detail="only from the laptop itself")
    raw = (await request.body())[:4096]
    if "application/json" in request.headers.get("content-type", ""):
        try:
            data = {k: (str(v) if v is not None else None) for k, v in json.loads(raw or b"{}").items()}
        except (ValueError, AttributeError):
            raise HTTPException(status_code=422, detail="bad JSON")
    else:
        data = {k: v[0] for k, v in parse_qs(raw.decode(errors="replace")).items()}
    home = f"{settings.web_base_url}/home"
    try:
        body = NewSession(name=data.get("name") or None, phone=data.get("phone") or None,
                          mic=_truthy(data.get("mic"), True),
                          labels=_truthy(data.get("labels"), False),
                          device=data.get("device") or None)
    except ValueError:
        return RedirectResponse(f"{home}?call_error=details", status_code=303)
    try:
        d = await _start_call(body, data.get("device_token") or None)
    except HTTPException as e:
        reason = {400: "no_stt", 401: "not_paired", 429: "busy"}.get(e.status_code, "failed")
        return RedirectResponse(f"{home}?call_error={reason}", status_code=303)
    return RedirectResponse(f"{d['elder_url']}#family={quote(d['family_url'], safe='')}",
                            status_code=303)


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
