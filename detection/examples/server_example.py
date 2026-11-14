"""Minimal example of how A's server can run the detector. Not production code.

Run:   pip install fastapi uvicorn && pip install -e detection
       uvicorn server_example:app --app-dir detection/examples
Then:  send caption JSON to ws://localhost:8000/captions/<session>
       listen for events on  ws://localhost:8000/events/<session>

What it shows (the parts that matter for B's package):
- One owner task per session. It's the only code that touches the Detector.
- Captions, ticks, the elder confirmation and the end of the call all go
  through one queue, in order.
- A tick every 1.0 s even during silence, so the meter can calm down.
What it leaves to A: Deepgram, the family-page token check, real session
management and cleanup.
"""
from __future__ import annotations

import asyncio
import logging
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from hangup_detect import Config, Detector, make_segment
from hangup_detect.llm_runner import LLMRunner

app = FastAPI()
log = logging.getLogger("hangup.server")
SESSIONS: dict[str, "Session"] = {}


class Session:
    def __init__(self, session_id: str):
        self.detector = Detector(Config(), session_id)
        # AI layer: on only if GROQ_API_KEY or GEMINI_API_KEY is set. Otherwise rules only.
        self.runner = LLMRunner.from_env(os.environ)
        self.queue: asyncio.Queue = asyncio.Queue()
        self.listeners: set[WebSocket] = set()
        self.loop = asyncio.get_running_loop()
        self.start = self.loop.time()
        self.tasks = [asyncio.create_task(self.owner()), asyncio.create_task(self.ticker())]

    def now(self) -> float:
        return self.loop.time() - self.start

    async def owner(self) -> None:
        """The only task that touches the detector. Messages were checked on arrival."""
        d = self.detector
        while True:
            kind, payload = await self.queue.get()
            if kind == "caption":
                out = d.feed(payload, self.now())
            elif kind == "set_elder":
                out = d.set_elder(payload, self.now())
            elif kind == "codeword_result":
                out = d.codeword_result(payload, self.now())
            elif kind == "llm":  # an AI answer, posted back by ask_llm below
                seq, result = payload
                out = d.llm_status(result.mode, self.now(), result.error)
                if result.raw:
                    out += d.apply_llm(seq, result.raw, self.now())
            elif kind == "tick":
                out = d.tick(self.now())
            else:  # "end"
                await self.broadcast(d.end(self.now()))
                return
            await self.broadcast(out)
            self.maybe_ask_llm()

    def maybe_ask_llm(self) -> None:
        """One AI request at a time. A new one goes out once a new caller line has arrived."""
        if self.runner is None or self.runner.busy:
            return
        req = self.detector.llm_request(self.now())
        if req is not None:
            asyncio.create_task(self.ask_llm(req))

    async def ask_llm(self, req) -> None:
        result = await self.runner.run(req)
        await self.queue.put(("llm", (req.seq, result)))  # applied by the owner, in order

    async def ticker(self) -> None:
        while not self.detector.ended:
            await asyncio.sleep(1.0)
            await self.queue.put(("tick", None))

    async def broadcast(self, events: list[dict]) -> None:
        for ws in list(self.listeners):
            try:
                for e in events:
                    await ws.send_json(e)
            except Exception:
                self.listeners.discard(ws)


def parse_message(msg) -> tuple[str, object] | None:
    """Turn one incoming JSON message into a queue item, or None if it's bad.

    Bad input is caught here so one malformed caption can't stop detection,
    and real errors inside the detector are never hidden.
    """
    if not isinstance(msg, dict):
        return None
    kind = msg.get("type")
    try:
        if kind == "caption":
            return kind, make_segment(msg["utterance_id"], msg["revision"], "unknown", msg["text"],
                                      msg["start_s"], msg["end_s"], msg["is_final"],
                                      speaker_raw=msg.get("speaker_raw"))
        if kind == "set_elder":
            return kind, msg.get("speaker_raw")
        if kind == "codeword_result":
            if not isinstance(msg["ok"], bool):
                raise TypeError("ok must be true or false")
            return kind, msg["ok"]
        if kind == "end":
            return kind, None
    except (KeyError, TypeError, ValueError) as exc:
        log.warning("bad %s message skipped: %s", kind, type(exc).__name__)  # never log text
        return None
    log.warning("ignoring unknown message type %r", kind)
    return None


def get_session(session_id: str) -> Session:
    if session_id not in SESSIONS:
        SESSIONS[session_id] = Session(session_id)
    return SESSIONS[session_id]


@app.websocket("/captions/{session_id}")
async def captions(ws: WebSocket, session_id: str):
    await ws.accept()
    s = get_session(session_id)
    try:
        while True:
            item = parse_message(await ws.receive_json())
            if item is not None:
                await s.queue.put(item)
    except WebSocketDisconnect:
        pass


@app.websocket("/events/{session_id}")
async def events(ws: WebSocket, session_id: str):
    # A: check the family-page token here before accepting (see CONTRACTS.md).
    await ws.accept()
    s = get_session(session_id)
    s.listeners.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        s.listeners.discard(ws)
