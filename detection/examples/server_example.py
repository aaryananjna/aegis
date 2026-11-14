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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from hangup_detect import Config, Detector, make_segment

app = FastAPI()
SESSIONS: dict[str, "Session"] = {}


class Session:
    def __init__(self, session_id: str):
        self.detector = Detector(Config(), session_id)
        self.queue: asyncio.Queue = asyncio.Queue()
        self.listeners: set[WebSocket] = set()
        self.loop = asyncio.get_running_loop()
        self.start = self.loop.time()
        self.tasks = [asyncio.create_task(self.owner()), asyncio.create_task(self.ticker())]

    def now(self) -> float:
        return self.loop.time() - self.start

    async def owner(self) -> None:
        """The only task that touches the detector."""
        d = self.detector
        while True:
            kind, msg = await self.queue.get()
            if kind == "caption":
                seg = make_segment(msg["utterance_id"], msg["revision"], "unknown", msg["text"],
                                   msg["start_s"], msg["end_s"], msg["is_final"],
                                   speaker_raw=msg.get("speaker_raw"))
                out = d.feed(seg, self.now())
            elif kind == "set_elder":
                out = d.set_elder(msg.get("speaker_raw"), self.now())
            elif kind == "tick":
                out = d.tick(self.now())
            else:  # "end"
                await self.broadcast(d.end(self.now()))
                return
            await self.broadcast(out)

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
            msg = await ws.receive_json()
            await s.queue.put((msg["type"], msg))  # "caption" | "set_elder" | "end"
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
