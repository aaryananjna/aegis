"""REFERENCE / FALLBACK server for Aegis. Not `server/`.

A small, complete server built to CONTRACTS.md v2.1 with B's detector, so that:
- A can copy the working parts into `server/` (same routes, tokens and close codes as the
  skeleton in `server/aegis_server/`), and
- the demo still runs if `server/` isn't ready (see docs/DEMO-RUNBOOK.md).

It has no microphone or Deepgram. Captions come in on WS /captions/{id} (localhost only)
or through POST /typed (the noisy-hall fallback). Everything lives in memory; no audio, no
caption text is logged.

Run (from the repo root):
    pip install -e detection fastapi "uvicorn[standard]"
    uvicorn aegis_dev_server:app --app-dir tools/dev_server --port 8000
"""
from __future__ import annotations

import asyncio
import hmac
import logging
import os
import secrets
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from hangup_detect import Config, Detector, make_segment
from hangup_detect.llm_runner import LLMRunner

log = logging.getLogger("aegis.dev_server")
app = FastAPI(title="Aegis dev server (reference / fallback)")

WEB_BASE_URL = os.environ.get("WEB_BASE_URL", "http://localhost:5173")
TICK_S = 1.0
BAD_TOKEN = 4401          # wrong, expired or other-role token (CONTRACTS C3)
POLICY_VIOLATION = 1008   # /captions from anywhere but the laptop
LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}
ROLES = ("elder", "family")
FAMILY_EVENTS = {"alert", "intervention", "codeword_ok", "status", "call_ended"}  # C4
CAPTIONS_INBOUND = {"caption", "set_elder", "end"}
ELDER_INBOUND = {"set_elder", "codeword_result"}


def allowed(role: str, event: dict) -> bool:
    return role == "elder" or event["type"] in FAMILY_EVENTS


class Session:
    """One call. The owner task is the only code that touches the detector."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.tokens = {role: secrets.token_urlsafe(16) for role in ROLES}
        self.detector = Detector(Config(), session_id)
        self.runner = LLMRunner.from_env(os.environ)  # AI layer only if a key is set
        self.queue: asyncio.Queue = asyncio.Queue()
        self.listeners: dict[WebSocket, str] = {}
        self.history: list[dict] = []  # every outbound event, for replay (C6); memory only
        self.send_lock = asyncio.Lock()  # a replay and a broadcast never interleave
        self.ended = False
        self.typed_count = 0
        self.loop = asyncio.get_running_loop()
        self.start = self.loop.time()
        self.tasks = [asyncio.create_task(self.owner()), asyncio.create_task(self.ticker())]

    def now(self) -> float:
        return self.loop.time() - self.start

    def check_token(self, role: str, token: str) -> bool:
        good = self.tokens.get(role)
        return bool(good) and not self.ended and hmac.compare_digest(good, token or "")

    async def owner(self) -> None:
        d = self.detector
        while True:
            kind, payload = await self.queue.get()
            now = self.now()
            if kind == "caption":
                seg, source = payload
                # C1: the caption goes out before the detector's events for it.
                out = [caption_event(self.session_id, seg, source, now)] + d.feed(seg, now)
            elif kind == "set_elder":
                out = d.set_elder(payload, now)
            elif kind == "codeword_result":
                out = d.codeword_result(payload, now)
            elif kind == "llm":
                seq, result = payload
                out = d.llm_status(result.mode, now, result.error)
                if result.raw:
                    out += d.apply_llm(seq, result.raw, now)
            elif kind == "tick":
                out = d.tick(now)
            else:  # "end" (C5)
                out = d.end(now) + [{"type": "call_ended", "session_id": self.session_id,
                                     "t": round(now, 3)}]
                await self.broadcast(out)
                await self.close()
                return
            await self.broadcast(out)
            self.maybe_ask_llm()

    def maybe_ask_llm(self) -> None:
        """B's pattern (detection/INTEGRATION.md): one AI request at a time, answer via the queue."""
        if self.runner is None or self.runner.busy:
            return
        req = self.detector.llm_request(self.now())
        if req is not None:
            asyncio.create_task(self._ask(req))

    async def _ask(self, req) -> None:
        result = await self.runner.run(req)
        await self.queue.put(("llm", (req.seq, result)))

    async def ticker(self) -> None:
        while not self.ended:
            await asyncio.sleep(TICK_S)
            await self.queue.put(("tick", None))

    async def broadcast(self, events: list[dict]) -> None:
        async with self.send_lock:
            self.history.extend(events)
            for ws, role in list(self.listeners.items()):
                try:
                    for e in events:
                        if allowed(role, e):
                            await ws.send_json(e)
                except Exception:
                    self.listeners.pop(ws, None)

    async def join(self, ws: WebSocket, role: str) -> None:
        """Replay this role's past events (C6), then register for live ones, with nothing missed."""
        async with self.send_lock:
            for e in self.history:
                if allowed(role, e):
                    await ws.send_json(e)
            self.listeners[ws] = role

    async def close(self) -> None:
        """Tokens stop working, history is dropped, listeners are let go."""
        self.ended = True
        self.history.clear()
        for ws in list(self.listeners):
            try:
                await ws.close()
            except Exception:
                pass
        self.listeners.clear()
        SESSIONS.pop(self.session_id, None)


SESSIONS: dict[str, Session] = {}


def caption_event(session_id: str, seg, source: str, t: float) -> dict:
    return {"type": "caption", "session_id": session_id, "t": round(t, 3),
            "utterance_id": seg.utterance_id, "revision": seg.revision,
            "speaker_raw": seg.speaker_raw, "text": seg.text, "start_s": seg.start_s,
            "end_s": seg.end_s, "is_final": seg.is_final, "source": source}


def parse(msg, allowed_types: set[str]):
    """One inbound JSON message → (kind, payload), or None if it's bad. Never logs text."""
    kind = msg.get("type") if isinstance(msg, dict) else None
    if kind not in allowed_types:
        log.warning("ignored message type %r", kind)
        return None
    try:
        if kind == "caption":
            source = msg.get("source", "live")
            seg = make_segment(msg["utterance_id"], msg["revision"], "unknown", msg["text"],
                               msg["start_s"], msg["end_s"], msg["is_final"],
                               speaker_raw=msg.get("speaker_raw"))
            return kind, (seg, source if source in ("live", "typed") else "live")
        if kind == "set_elder":
            return kind, msg.get("speaker_raw")
        if kind == "codeword_result":
            if not isinstance(msg["ok"], bool):  # never coerce "false" (issue #10)
                raise TypeError("ok must be true or false")
            return kind, msg["ok"]
        return kind, None  # end
    except (KeyError, TypeError, ValueError) as exc:
        log.warning("bad %s message skipped: %s", kind, type(exc).__name__)
        return None


def is_local(host: str | None) -> bool:
    return host in LOCAL_HOSTS


def require_local(request: Request) -> None:
    if not is_local(request.client.host if request.client else None):
        raise HTTPException(status_code=403, detail="only from the laptop itself")


# ---- HTTP ------------------------------------------------------------------------------

class NewSession(BaseModel):
    name: str | None = None   # display only, e.g. "Rose" (made up in demos)
    phone: str | None = None  # display only, for the family page's call button


class Typed(BaseModel):
    session_id: str
    text: str
    speaker_raw: str | None = "1"  # the caller's voice in the demo; null = no labels


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "server": "dev_server", "sessions": len(SESSIONS),
            "ai_layer": bool(os.environ.get("GROQ_API_KEY") or os.environ.get("GEMINI_API_KEY"))}


@app.post("/sessions")
async def create_session(request: Request, body: NewSession | None = None) -> dict:
    require_local(request)
    sid = secrets.token_urlsafe(6)
    s = SESSIONS[sid] = Session(sid)
    extra = {k: v for k, v in (("name", body and body.name), ("phone", body and body.phone)) if v}
    urls = {role: f"{WEB_BASE_URL}/{role}?" + urlencode(
        {"session": sid, "token": s.tokens[role], **(extra if role == "family" else {})})
        for role in ROLES}
    print(f"\n  Aegis session {sid}\n  elder:  {urls['elder']}\n  family: {urls['family']}\n",
          flush=True)
    return {"session_id": sid, "elder_url": urls["elder"], "family_url": urls["family"]}


@app.post("/sessions/{session_id}/end")
async def end_session(session_id: str, request: Request) -> dict:
    require_local(request)
    s = SESSIONS.get(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="no such session")
    await s.queue.put(("end", None))
    return {"ok": True}


@app.post("/typed")
async def typed(body: Typed, request: Request) -> dict:
    """Noisy-hall fallback: a typed line becomes a final caption with source "typed"."""
    require_local(request)
    s = SESSIONS.get(body.session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="no such session")
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="text is empty")
    s.typed_count += 1
    now = s.now()
    seg = make_segment(f"typed-{s.typed_count}", 0, "unknown", text, now, now, True,
                       speaker_raw=body.speaker_raw)
    await s.queue.put(("caption", (seg, "typed")))
    return {"ok": True, "utterance_id": seg.utterance_id}


# ---- WebSockets --------------------------------------------------------------------------

@app.websocket("/captions/{session_id}")
async def captions(ws: WebSocket, session_id: str) -> None:
    if not is_local(ws.client.host if ws.client else None):
        await ws.close(code=POLICY_VIOLATION)
        return
    s = SESSIONS.get(session_id)
    if s is None:
        await ws.close(code=BAD_TOKEN)
        return
    await ws.accept()
    try:
        while True:
            item = parse(await ws.receive_json(), CAPTIONS_INBOUND)
            if item is not None:
                await s.queue.put(item)
    except WebSocketDisconnect:
        pass


@app.websocket("/events/{session_id}")
async def events(ws: WebSocket, session_id: str, role: str = "", token: str = "") -> None:
    s = SESSIONS.get(session_id)
    if role not in ROLES or s is None or not s.check_token(role, token):
        await ws.close(code=BAD_TOKEN)  # same answer for every failure: don't leak which
        return
    await ws.accept()
    await s.join(ws, role)
    try:
        while True:
            msg = await ws.receive_json()
            if role == "elder":
                item = parse(msg, ELDER_INBOUND)
                if item is not None:
                    await s.queue.put(item)
    except WebSocketDisconnect:
        s.listeners.pop(ws, None)
