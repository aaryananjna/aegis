"""Demo-critical fixes from Mihir's server review (#77). No network, no mic, no database."""
from __future__ import annotations

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from aegis_server import db
from aegis_server import sessions as sessions_mod
from aegis_server.main import app
from aegis_server.routes import captions_ws, sessions as sessions_route
from aegis_server.stt import deepgram


@pytest.fixture
def client(monkeypatch):
    async def no_db(*a, **k):
        return None
    monkeypatch.setattr(db, "connect", no_db)
    monkeypatch.setattr(sessions_route, "is_laptop", lambda conn: True)
    monkeypatch.setattr(captions_ws, "is_laptop", lambda conn: True)
    monkeypatch.setattr(sessions_mod.LLMRunner, "from_env", staticmethod(lambda env: None))
    with TestClient(app) as c:
        yield c


def _start(c: TestClient, **body) -> tuple[str, str]:
    d = c.post("/sessions", json=body).json()
    return d["session_id"], d["elder_url"].split("token=")[1].split("&")[0]


def _drain(ws) -> list[dict]:
    got = []
    while True:
        e = ws.receive_json()
        got.append(e)
        if e["type"] == "call_ended":
            return got


# ---- 1. a new mic call ends the old one ---------------------------------------------------

def test_new_mic_call_ends_the_old_one(client, monkeypatch):
    monkeypatch.setattr(deepgram, "check_mic", lambda device: None)
    monkeypatch.setattr(sessions_mod.settings.__class__, "deepgram_api_key", "test-key")
    started = []

    def fake_start_mic(self, device, labels=True):  # no real mic or Deepgram in tests
        self.mic_on = True
        started.append(self.session_id)
    monkeypatch.setattr(sessions_mod.Session, "start_mic", fake_start_mic)

    old, token = _start(client, mic=True, labels=False)
    with client.websocket_connect(f"/events/{old}?role=elder&token={token}") as ws:
        new, _ = _start(client, mic=True, labels=False)
        assert _drain(ws)[-1]["type"] == "call_ended"  # the old call ended by itself
    assert started == [old, new]
    assert client.get("/health").json()["sessions"] == 1
    client.post(f"/sessions/{new}/end")


def test_calls_without_the_mic_are_left_alone(client):
    a, _ = _start(client)
    b, _ = _start(client)
    assert client.get("/health").json()["sessions"] == 2
    client.post(f"/sessions/{a}/end")
    client.post(f"/sessions/{b}/end")


# ---- 2. a bad mic fails the start --------------------------------------------------------

def test_bad_mic_fails_with_400_and_no_call_starts(client, monkeypatch):
    monkeypatch.setattr(sessions_mod.settings.__class__, "deepgram_api_key", "test-key")

    def no_such_mic(device):
        raise deepgram.SttError(f"can't use mic {device!r}: no such device")
    monkeypatch.setattr(deepgram, "check_mic", no_such_mic)
    r = client.post("/sessions", json={"mic": True, "device": "No Such Mic"})
    assert r.status_code == 400 and "No Such Mic" in r.json()["detail"]
    assert client.get("/health").json()["sessions"] == 0


# ---- 3. screens hear about caption trouble ------------------------------------------------

def test_two_failed_reconnects_call_on_trouble_once(monkeypatch):
    calls = {"trouble": 0}

    def refuse(*a, **k):
        raise OSError("network down")
    monkeypatch.setattr(deepgram.websockets, "connect", refuse)
    monkeypatch.setattr(deepgram.asyncio, "sleep", _fast_sleep)

    async def trouble():
        calls["trouble"] += 1

    async def sink(cap):
        pass

    async def audio():
        for _ in range(400):
            yield b"\0" * deepgram.CHUNK_BYTES
            await _fast_sleep(0)

    async def run():
        stop = asyncio.Event()
        task = asyncio.create_task(deepgram.transcribe(
            "s1", audio(), sink, api_key="k", stop=stop, on_trouble=trouble))
        await _real_sleep(0.3)
        stop.set()  # transcribe stops by itself once stop is set
        try:
            await asyncio.wait_for(task, 2)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
    asyncio.run(run())
    assert calls["trouble"] == 1


_real_sleep = asyncio.sleep


async def _fast_sleep(s):
    await _real_sleep(0)


# ---- 4. detector errors don't swallow captions or call_ended -------------------------------

def test_caption_still_reaches_screen_if_detector_fails(client, monkeypatch):
    def boom(self, seg, now):
        raise RuntimeError("detector bug")
    monkeypatch.setattr(sessions_mod.Detector, "feed", boom)
    sid, token = _start(client)
    with client.websocket_connect(f"/events/{sid}?role=elder&token={token}") as ws:
        client.post("/typed", json={"session_id": sid, "text": "Hello?", "speaker_raw": None})
        time.sleep(0.3)
        client.post(f"/sessions/{sid}/end")
        events = _drain(ws)
    assert [e["text"] for e in events if e["type"] == "caption"] == ["Hello?"]


def test_call_ended_goes_out_even_if_detector_end_fails(client, monkeypatch):
    def boom(self, now):
        raise RuntimeError("detector bug")
    monkeypatch.setattr(sessions_mod.Detector, "end", boom)
    sid, token = _start(client)
    with client.websocket_connect(f"/events/{sid}?role=elder&token={token}") as ws:
        client.post(f"/sessions/{sid}/end")
        assert _drain(ws)[-1]["type"] == "call_ended"
    assert client.get("/health").json()["sessions"] == 0
