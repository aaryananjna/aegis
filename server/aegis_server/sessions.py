"""One Session per call (CONTRACTS v2.1, "Rules for A's server").

- One owner task is the only code that touches the Detector. Captions, ticks, set_elder,
  codeword_result, llm and end all go through one asyncio.Queue, in order.
- A tick every second, even in silence.
- Two random tokens per session, one per role, compared in constant time. They stop working
  when the session ends.
- Every screen has its own outbox and writer task, so a slow or stuck phone can't stall the
  detector or the other screens. A screen that falls too far behind is disconnected; when it
  reconnects it gets the replay.
- Event history for replay on reconnect (C6) lives in memory only and is dropped at the end.
- Limits: MAX_SESSIONS calls at once, MAX_LISTENERS screens per role per call (the oldest is
  dropped for a newer one, so a phone that reconnects always gets in), MAX_CALL_S per call.
- Who is the grandparent, without a tap (proposal, issue to B and C): she's answering an
  incoming call, so the first line of the call is normally her "Hello?". If that first live line
  is a short greeting (GREETING_MAX_WORDS words or fewer, in the first GREETING_WINDOW_S
  seconds, with a speaker label), the server sends set_elder for that voice itself. If the first
  line is long (a robocall, or the caller talking first) it doesn't guess, and the screen asks
  for the tap as before. A tap always wins: it replaces the guess, and once anyone has tapped
  the server never guesses. Screens get an `elder_set` event (elder only) saying who was picked
  and how ("server" or "tap"). AUTO_ELDER=0 turns the guess off.
"""
from __future__ import annotations

import asyncio
import contextlib
import hmac
import logging
import os
import re
import secrets
from collections import deque

from fastapi import WebSocket
from hangup_detect import Config, Detector
from hangup_detect.llm_runner import LLMRunner

from . import db
from .config import settings
from .history import CallRecorder
from .test_transcript import TestTranscript
from .messages import parse
from .roles import ROLES, allowed

log = logging.getLogger("aegis.sessions")

MAX_SESSIONS = 8
MAX_LISTENERS = 4          # per role, per call
MAX_CALL_S = 2 * 3600      # a call that runs this long is ended
MAX_HISTORY = 20_000       # events kept for replay; a 2-hour call stays well under this
OUTBOX = 2_000             # events a screen may fall behind before it's disconnected
QUEUE = 1_000              # inbound items waiting for the owner
GREETING_MAX_WORDS = 5     # "Hello?", "Hi, who's this?", "Hello, this is Rose."
GREETING_WINDOW_S = 30.0   # only guess from a line in the first 30 s of the call
AUTO_ELDER = os.getenv("AUTO_ELDER", "1") != "0"

_WORD = re.compile(r"[A-Za-z0-9']+")


def is_greeting(text: str) -> bool:
    n = len(_WORD.findall(text))
    return 0 < n <= GREETING_MAX_WORDS


_WRITERS: set[asyncio.Task] = set()

# AI answers since the server started, by provider. Numbers only; shown on GET /health.
AI_ANSWERS: dict[str, int] = {"groq": 0, "gemini": 0, "failed": 0}


class Listener:
    def __init__(self, ws: WebSocket, role: str) -> None:
        self.ws = ws
        self.role = role
        self.outbox: asyncio.Queue[dict | None] = asyncio.Queue()
        self.writer: asyncio.Task | None = None
        self.closed = False

    def send(self, event: dict) -> bool:
        """Queue one event; False if this screen is too far behind."""
        if self.closed:
            return False
        if self.outbox.qsize() >= OUTBOX:
            return False
        self.outbox.put_nowait(event)
        return True

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            self.outbox.put_nowait(None)

    async def write(self, on_done) -> None:
        try:
            while True:
                e = await self.outbox.get()
                if e is None:
                    break
                await self.ws.send_json(e)
        except Exception:
            pass
        finally:
            self.closed = True
            with contextlib.suppress(Exception):
                await self.ws.close()
            on_done(self)


class Session:
    def __init__(self, session_id: str, store: "SessionStore", elder_id=None,
                 save_transcript: bool = False) -> None:
        self.session_id = session_id
        self.store = store
        self.tokens = {role: secrets.token_urlsafe(32) for role in ROLES}
        self.detector = Detector(Config(), session_id)
        self.runner = LLMRunner.from_env(os.environ)  # AI layer only if a key is set
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE)
        self.listeners: list[Listener] = []
        self.history: deque[dict] = deque(maxlen=MAX_HISTORY)
        self.ended = False
        self.typed_count = 0
        # Who picked the grandparent's voice: None (nobody yet), "server" (guessed from the first
        # greeting), "tap" (the screen or the laptop). "declined": the first line wasn't a
        # greeting, so the server won't guess for this call.
        self.elder_pick: str | None = None
        # Call history in TigerDB, only for calls from a paired laptop (numbers only).
        self.recorder = None
        # Test transcripts (opt-in, staged calls only): a local .call file, never the database.
        self.transcript = TestTranscript(session_id) if save_transcript else None
        self.elder_raw: str | None = None
        if elder_id is not None and db.is_open():
            self.recorder = CallRecorder(session_id, elder_id)
        self.loop = asyncio.get_running_loop()
        self.start = self.loop.time()
        self.stt_stop = asyncio.Event()
        self.side_tasks: set[asyncio.Task] = set()  # ticker, mic, AI requests
        self.owner_task = asyncio.create_task(self.owner())
        self._spawn(self.ticker())

    # ---- basics ------------------------------------------------------------------------

    def _spawn(self, coro) -> asyncio.Task:
        t = asyncio.create_task(coro)
        self.side_tasks.add(t)
        t.add_done_callback(self.side_tasks.discard)
        return t

    def now(self) -> float:
        return self.loop.time() - self.start

    def check_token(self, role: str, token: str) -> bool:
        good = self.tokens.get(role)
        if not good or self.ended or not isinstance(token, str):
            return False
        return hmac.compare_digest(good.encode(), token.encode())

    async def put(self, item) -> None:
        if not self.ended:
            await self.queue.put(item)

    # ---- the owner: the only code that touches the detector ------------------------------

    async def owner(self) -> None:
        d = self.detector
        while True:
            kind, payload = await self.queue.get()
            now = self.now()
            try:
                if kind == "caption":
                    seg, source = payload
                    # C1: the caption goes out before the detector's events for it.
                    out = [self._caption_event(seg, source, now)] + d.feed(seg, now)
                    if self.transcript:
                        self.transcript.add(seg)
                    out += self._maybe_guess_elder(seg, source, now)
                elif kind == "set_elder":  # a tap (or the laptop) always wins
                    self.elder_pick = "tap"
                    self.elder_raw = payload
                    out = d.set_elder(payload, now) + [self._elder_set(payload, "tap", now)]
                elif kind == "no_labels":  # labels off: score everyone from line one
                    out = d.set_elder(None, now) + [self._elder_set(None, "server", now)]
                elif kind == "codeword_result":
                    out = d.codeword_result(payload, now)
                elif kind == "llm":
                    seq, result = payload
                    out = d.llm_status(result.mode, now, result.error)
                    if result.raw:
                        out += d.apply_llm(seq, result.raw, now)
                elif kind == "tick":
                    out = d.tick(now)
                    if self.recorder:
                        self.recorder.sample()
                elif kind == "status":  # from the server itself (C7), no seq
                    out = [{"type": "status", "session_id": self.session_id,
                            "t": round(now, 3), **payload}]
                else:  # "end" (C5)
                    out = d.end(now) + [{"type": "call_ended", "session_id": self.session_id,
                                         "t": round(now, 3)}]
                    if self.recorder:
                        self.recorder.observe(out)
                        self.recorder.finish()
                    if self.transcript:
                        self.transcript.write(self.elder_raw)
                    self.broadcast(out)
                    self.close()
                    return
            except Exception as e:  # one bad item must never stop detection
                log.error("session %s: %s on %s item", self.session_id, type(e).__name__, kind)
                continue
            if self.recorder:
                self.recorder.observe(out)
            self.broadcast(out)
            self._maybe_ask_llm()

    def _maybe_guess_elder(self, seg, source: str, now: float) -> list[dict]:
        """After the first live final line: set_elder for that voice if it's a short greeting."""
        if not AUTO_ELDER or self.elder_pick is not None or source != "live":
            return []
        if not seg.is_final or not seg.text.strip():
            return []
        if seg.speaker_raw is None or now > GREETING_WINDOW_S or not is_greeting(seg.text):
            self.elder_pick = "declined"  # no labels, too late or not a greeting: wait for a tap
            log.info("session %s: first line isn't a short greeting; waiting for the tap",
                     self.session_id)
            return []
        self.elder_pick = "server"
        self.elder_raw = seg.speaker_raw
        log.info("session %s: grandparent guessed from the first greeting (voice %s)",
                 self.session_id, seg.speaker_raw)
        return (self.detector.set_elder(seg.speaker_raw, now)
                + [self._elder_set(seg.speaker_raw, "server", now)])

    def _elder_set(self, speaker_raw, by: str, now: float) -> dict:
        """Server event (no seq), elder screens only: whose voice is the grandparent's."""
        return {"type": "elder_set", "session_id": self.session_id, "t": round(now, 3),
                "speaker_raw": speaker_raw, "by": by}

    def _caption_event(self, seg, source: str, now: float) -> dict:
        return {"type": "caption", "session_id": self.session_id, "t": round(now, 3),
                "utterance_id": seg.utterance_id, "revision": seg.revision,
                "speaker_raw": seg.speaker_raw, "text": seg.text, "start_s": seg.start_s,
                "end_s": seg.end_s, "is_final": seg.is_final, "source": source}

    def _maybe_ask_llm(self) -> None:
        """C15: one AI request at a time; the answer comes back through the queue."""
        if self.runner is None or self.runner.busy or self.ended:
            return
        req = self.detector.llm_request(self.now())
        if req is not None:
            self._spawn(self._ask(req))

    async def _ask(self, req) -> None:
        try:
            result = await self.runner.run(req)
        except Exception as e:
            AI_ANSWERS["failed"] += 1
            log.warning("session %s: AI layer failed (%s)", self.session_id, type(e).__name__)
            return
        # Which AI answered (groq, or gemini as backup), so /health shows it really fires.
        key = (result.provider or "failed") if result.raw else "failed"
        AI_ANSWERS[key] = AI_ANSWERS.get(key, 0) + 1
        if not result.raw:
            log.warning("session %s: AI gave no answer (%s)", self.session_id, result.error)
        await self.put(("llm", (req.seq, result)))

    async def ticker(self) -> None:
        while not self.ended:
            await asyncio.sleep(settings.tick_s)
            if self.now() > MAX_CALL_S:
                await self.put(("end", None))
                return
            with contextlib.suppress(asyncio.QueueFull):
                self.queue.put_nowait(("tick", None))  # skip a tick rather than pile up

    # ---- screens -------------------------------------------------------------------------

    def broadcast(self, events: list[dict]) -> None:
        """Record events and queue each for every screen whose role allows it. Never awaits,
        so it can't be slowed by a screen, and it can't interleave with join()."""
        self.history.extend(events)
        for lis in list(self.listeners):
            for e in events:
                if allowed(lis.role, e) and not lis.send(e):
                    log.warning("session %s: %s screen too slow, disconnected",
                                self.session_id, lis.role)
                    lis.close()
                    break

    def join(self, ws: WebSocket, role: str) -> Listener:
        """Replay this role's past events (C6), then live ones. Synchronous, so no event can
        land between the replay and the registration."""
        same = [x for x in self.listeners if x.role == role]
        if len(same) >= MAX_LISTENERS:
            same[0].close()  # drop the oldest: a reconnecting phone must always get in
        lis = Listener(ws, role)
        for e in self.history:
            if allowed(role, e):
                lis.outbox.put_nowait(e)
        self.listeners.append(lis)
        lis.writer = asyncio.create_task(lis.write(self._gone))  # ends after its last event
        _WRITERS.add(lis.writer)  # asyncio keeps only weak references to tasks
        lis.writer.add_done_callback(_WRITERS.discard)
        return lis

    def _gone(self, lis: Listener) -> None:
        with contextlib.suppress(ValueError):
            self.listeners.remove(lis)

    # ---- live captions from the laptop mic (inside the server) ---------------------------

    def start_mic(self, device: int | str | None, labels: bool = True) -> None:
        """Live captions from the laptop mic. labels=False: no speaker labels, every line is
        scored from the start (set_elder(None) now), and the server never guesses a voice."""
        from .stt import deepgram

        if not labels:
            self.elder_pick = "server"
            self.queue.put_nowait(("no_labels", None))

        async def sink(cap: dict) -> None:
            item = parse(cap, {"caption"})
            if item is not None:
                await self.put(item)

        async def on_connect() -> None:
            await self.put(("status", {"stt": "deepgram", "warning": None}))

        async def run() -> None:
            try:
                await deepgram.transcribe(
                    self.session_id, deepgram.mic_chunks(device, self.stt_stop), sink,
                    api_key=settings.deepgram_api_key, stop=self.stt_stop,
                    on_connect=on_connect, diarize=labels)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                msg = str(e) if isinstance(e, deepgram.SttError) else type(e).__name__
                log.error("session %s: live captions stopped: %s", self.session_id, msg)
                await self.put(("status", {"stt": "none",
                                           "warning": "live captions stopped"}))

        self._spawn(run())

    # ---- the end -------------------------------------------------------------------------

    def close(self) -> None:
        """Tokens stop working, the mic stops, history is dropped, screens are let go after
        their last events (call_ended) are sent."""
        if self.ended:
            return
        self.ended = True
        self.stt_stop.set()
        self.history.clear()
        for lis in list(self.listeners):
            lis.close()
        self.store.drop(self.session_id)
        for t in list(self.side_tasks):  # ticker, mic (audio stops at once), AI requests
            t.cancel()
        if asyncio.current_task() is not self.owner_task:
            self.owner_task.cancel()


class TooManySessions(Exception):
    pass


class SessionStore:
    """All live sessions, in memory only."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self, elder_id=None, save_transcript: bool = False) -> Session:
        if len(self._sessions) >= MAX_SESSIONS:
            raise TooManySessions
        sid = secrets.token_urlsafe(9)
        s = self._sessions[sid] = Session(sid, self, elder_id, save_transcript)
        return s

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def drop(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def __len__(self) -> int:
        return len(self._sessions)

    async def close_all(self) -> None:
        for s in list(self._sessions.values()):
            await s.put(("end", None))


store = SessionStore()
