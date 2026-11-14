"""Shared helpers for the contract tests (fixtures are in conftest.py) (CONTRACTS.md v2.1).

Everything here is test plumbing. The behavior being checked lives in the test_contract_*.py
files. Nothing needs server/.env, a database or the network: the detector runs rules only.

Assumptions about A's choices that the contract leaves open, kept in one place so they're easy
to change:
- `elder_url` and `family_url` carry the token as a `token=` query parameter (the contract's
  suggestion: http://localhost:5173/elder?session=…&token=…).
- The TestClient is used as a context manager, so every request and WebSocket shares one event
  loop and the session's owner and ticker tasks keep running between them.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

import anyio

REPO = Path(__file__).resolve().parents[2]
SCAM_FIXTURE = REPO / "detection" / "fixtures" / "events-scam-grandson.jsonl"
BENIGN_FIXTURE = REPO / "detection" / "fixtures" / "events-benign-party.jsonl"

LOCALHOST = ("127.0.0.1", 50000)
HOTSPOT_PHONE = ("192.168.1.23", 50000)  # another device on the same Wi-Fi

# C4: the only event types a family listener may ever receive.
FAMILY_TYPES = {"alert", "intervention", "codeword_ok", "status", "call_ended"}
# Events the detector emits carry seq (Envelope section). Server-added events don't.
DETECTOR_TYPES = {"tactic_set", "risk", "intervention", "alert", "codeword_ok", "status"}

RECV_TIMEOUT_S = 5.0


# ---- sessions and URLs ---------------------------------------------------------------------
def token_of(url: str) -> str:
    tokens = parse_qs(urlparse(url).query).get("token")
    assert tokens and tokens[0], f"no token= in {url!r}"
    return tokens[0]


class Call:
    """One session made with POST /sessions."""

    def __init__(self, body: dict):
        self.body = body
        self.id: str = body["session_id"]
        self.elder_token = token_of(body["elder_url"])
        self.family_token = token_of(body["family_url"])

    def events_url(self, role: str, token: str | None = None) -> str:
        if token is None:
            token = self.elder_token if role == "elder" else self.family_token
        return f"/events/{self.id}?role={role}&token={quote(token)}"

    @property
    def captions_url(self) -> str:
        return f"/captions/{self.id}"


# ---- receiving with a timeout --------------------------------------------------------------
def recv(ws, timeout: float = RECV_TIMEOUT_S) -> dict:
    """ws.receive_json() that fails after `timeout` seconds instead of hanging the suite.

    Uses two private attributes of starlette's WebSocketTestSession (`portal`, `_send_rx`);
    if a starlette upgrade renames them, this is the one place to fix.
    """
    async def get():
        with anyio.fail_after(timeout):
            return await ws._send_rx.receive()

    msg = ws.portal.call(get)
    ws._raise_on_close(msg)  # raises WebSocketDisconnect on a close frame
    return json.loads(msg["text"])


def recv_until(ws, pred, timeout: float = RECV_TIMEOUT_S, limit: int = 500) -> list[dict]:
    """Receive events until one matches `pred`. Returns all of them, the match last."""
    seen: list[dict] = []
    deadline = time.monotonic() + timeout
    for _ in range(limit):
        e = recv(ws, max(0.01, deadline - time.monotonic()))
        seen.append(e)
        if pred(e):
            return seen
    raise AssertionError(f"no matching event in {limit} events")


def is_type(t: str, **fields):
    return lambda e: e.get("type") == t and all(e.get(k) == v for k, v in fields.items())


def drain(ws, quiet_s: float = 0.3) -> list[dict]:
    """Everything that arrives until the socket has been quiet for `quiet_s`."""
    out: list[dict] = []
    while True:
        try:
            out.append(recv(ws, quiet_s))
        except TimeoutError:
            return out


# ---- scam calls ----------------------------------------------------------------------------
def fixture_captions(path: Path = SCAM_FIXTURE) -> list[dict]:
    """The inbound caption messages of a fixture call (B's fixture minus the server's `t`)."""
    caps = []
    for line in path.read_text().splitlines():
        e = json.loads(line)
        if e["type"] == "caption":
            e.pop("t", None)
            e.pop("session_id", None)
            e.setdefault("source", "live")
            caps.append(e)
    return caps


SCAM = fixture_captions(SCAM_FIXTURE)
# The grandson scam: the codeword card fires on u5 ("bail money … gift cards") and the
# hangup card on u7 ("there's no time for that"), once speaker "0" is confirmed as Nana.
SCAM_UNTIL_CODEWORD = [c for c in SCAM if c["utterance_id"] <= "u5"]
SCAM_AFTER_CODEWORD = [c for c in SCAM if c["utterance_id"] > "u5"]


def send_call(cap_ws, call: Call, captions: list[dict], elder: str | None = "0") -> None:
    """Confirm the grandparent, then send captions on /captions, in order."""
    if elder is not None:
        cap_ws.send_json({"type": "set_elder", "speaker_raw": elder})
    for c in captions:
        cap_ws.send_json({**c, "session_id": call.id})


# ---- watching the detector -----------------------------------------------------------------
class DetectorSpy:
    """Records every call the server makes into hangup_detect.Detector (any session)."""

    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []

    def names(self, name: str) -> list[tuple]:
        return [args for n, args in self.calls if n == name]
