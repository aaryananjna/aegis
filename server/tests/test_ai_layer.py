"""The AI layer fires alongside the rules, through the server (C15, #16, #47, #55).

Groq and Gemini are faked (no network, no quota), the same way detection/tests/test_s8a_llm.py
does it. The live check against the real providers is `server/scripts/ai-check`.

Each call runs the demo's labels-off mode: set_elder(null), then typed caller lines.
"""
from __future__ import annotations

import json
import re
import time

import pytest
from fastapi.testclient import TestClient
from hangup_detect.llm_runner import LLMRunner

from aegis_server import sessions as sessions_mod
from aegis_server.main import app
from aegis_server.routes import captions_ws, sessions as sessions_route

# Worded so the rules alone hardly react: only the AI can make these count.
# One line, because the detector asks the AI at most once per 8 s (llm_min_interval_s).
SOFT_SCAM = [
    "Hey, it's your nephew, I'm stuck at the station. Pick up some of those store cards "
    "and read me the codes on the back.",
]
RULES_SCAM = [
    "Grandma it's me, I got in a car accident and I'm in jail.",
    "I need bail money right now, buy gift cards and read me the numbers.",
    "Please don't tell Mom, keep it a secret.",
]


class FakeAI:
    """Stands in for http_transport. Per provider: "answer", "down" or "slow"."""

    def __init__(self, **behaviour: str) -> None:
        self.behaviour = behaviour
        self.calls: list[str] = []

    def __call__(self, provider: str, messages: list[dict], timeout_s: float) -> str:
        self.calls.append(provider)
        how = self.behaviour.get(provider, "down")
        if how == "down":
            raise OSError(f"{provider} is down")
        if how == "slow":
            time.sleep(timeout_s + 0.3)
            return "{}"
        # Answer like a real model: quote the "store cards" line back with its id.
        tactics = []
        for m in re.finditer(r"^\[([^\]]+)\] (.*)$", messages[-1]["content"], re.M):
            uid, text = m.groups()
            if "store cards" in text:
                tactics.append({"tactic": "payment", "utterance_id": uid, "quote": "store cards"})
            if "your nephew" in text:
                tactics.append({"tactic": "impersonation", "utterance_id": uid,
                                "quote": "it's your nephew"})
        return json.dumps({"tactics": tactics})


@pytest.fixture
def ai(monkeypatch):
    """Install a fake AI for every new call; returns a function to choose its behaviour."""
    state = {"fake": None, "providers": ["groq", "gemini"], "budget": 1.5}

    def from_env(env):
        if state["fake"] is None:
            return None  # no keys: rules only
        return LLMRunner(state["fake"], state["providers"], total_s=state["budget"],
                         socket_s=min(1.2, state["budget"]))

    monkeypatch.setattr(sessions_mod.LLMRunner, "from_env", staticmethod(from_env))
    # The test client isn't on loopback; treat it as the laptop for these tests.
    monkeypatch.setattr(sessions_route, "is_laptop", lambda conn: True)
    monkeypatch.setattr(captions_ws, "is_laptop", lambda conn: True)
    for k in sessions_mod.AI_ANSWERS:
        sessions_mod.AI_ANSWERS[k] = 0

    def use(fake: FakeAI | None, budget: float = 1.5) -> FakeAI | None:
        state["fake"], state["budget"] = fake, budget
        return fake

    return use


@pytest.fixture
def client(monkeypatch):
    """One client for the whole test, so the call's background tasks keep running. No
    accounts database: these tests are about calls."""
    from aegis_server import db
    async def no_db(*a, **k):
        return None
    monkeypatch.setattr(db, "connect", no_db)
    with TestClient(app) as c:
        yield c


def run_call(c: TestClient, lines: list[str], wait_s: float = 3.0) -> list[dict]:
    """A labels-off call with typed caller lines; returns everything the elder screen got."""
    d = c.post("/sessions", json={}).json()
    sid = d["session_id"]
    token = d["elder_url"].split("token=")[1].split("&")[0]
    got: list[dict] = []
    with c.websocket_connect(f"/events/{sid}?role=elder&token={token}") as ws:
        ws.send_json({"type": "set_elder", "speaker_raw": None})
        for line in lines:
            assert c.post("/typed", json={"session_id": sid, "text": line,
                                          "speaker_raw": None}).status_code == 200
            time.sleep(0.4)
        time.sleep(wait_s)
        c.post(f"/sessions/{sid}/end")
        while True:
            e = ws.receive_json()
            got.append(e)
            if e["type"] == "call_ended":
                break
    return got


def ai_evidence(events: list[dict]) -> set[str]:
    return {ev["tactic"] for e in events if e["type"] == "tactic_set"
            for ev in e.get("evidence", []) if ev.get("source") == "llm"}


def rule_evidence(events: list[dict]) -> set[str]:
    return {ev["tactic"] for e in events if e["type"] == "tactic_set"
            for ev in e.get("evidence", []) if ev.get("source") == "rule"}


def modes(events: list[dict]) -> list[str]:
    return [e["mode"] for e in events if e["type"] == "status" and e.get("mode")]


def test_groq_answers_and_its_evidence_reaches_the_screen(ai, client):
    fake = ai(FakeAI(groq="answer"))
    events = run_call(client, SOFT_SCAM)
    assert "groq" in fake.calls and "gemini" not in fake.calls
    assert {"payment", "impersonation"} <= ai_evidence(events)
    assert "full" in modes(events)
    assert sessions_mod.AI_ANSWERS["groq"] >= 1


def test_ai_and_rules_fire_together(ai, client):
    ai(FakeAI(groq="answer"))
    events = run_call(client, SOFT_SCAM + RULES_SCAM)  # the AI's first look sees the soft line
    assert rule_evidence(events), "the rules should still fire"
    assert ai_evidence(events), "the AI should add its own evidence on top"
    assert any(e["type"] == "intervention" for e in events)


def test_gemini_takes_over_when_groq_is_down(ai, client):
    fake = ai(FakeAI(groq="down", gemini="answer"))
    events = run_call(client, SOFT_SCAM)
    assert fake.calls[:2] == ["groq", "gemini"]
    assert "payment" in ai_evidence(events)
    assert sessions_mod.AI_ANSWERS["gemini"] >= 1 and sessions_mod.AI_ANSWERS["groq"] == 0


def test_both_down_falls_back_to_rules_and_says_so(ai, client):
    ai(FakeAI(groq="down", gemini="down"))
    events = run_call(client, RULES_SCAM)
    assert not ai_evidence(events)
    assert rule_evidence(events) and any(e["type"] == "intervention" for e in events)
    # The detector only sends status when the mode changes, and it never left rules_only,
    # so the screen hears nothing. /health's counter is where the failures show.
    assert "full" not in modes(events)
    assert sessions_mod.AI_ANSWERS["failed"] >= 1


def test_slow_ai_never_holds_up_captions(ai, client):
    ai(FakeAI(groq="slow"), budget=0.3)
    start = time.monotonic()
    events = run_call(client, RULES_SCAM, wait_s=1.0)
    captions = [e for e in events if e["type"] == "caption"]
    assert len(captions) == len(RULES_SCAM)  # every line still reached the screen
    assert any(e["type"] == "intervention" for e in events)  # rules carried on alone
    assert time.monotonic() - start < 8


def test_ai_looks_again_after_8_seconds(ai, client):
    """First look on the first line; the next one waits for llm_min_interval_s (8 s)."""
    fake = ai(FakeAI(groq="answer"))
    events = run_call(client, ["Hey, it's your nephew, I'm stuck at the station.",
                               "Pick up some of those store cards and read me the codes."],
                      wait_s=9.5)
    assert fake.calls.count("groq") >= 2
    assert {"impersonation", "payment"} <= ai_evidence(events)


def test_no_keys_means_rules_only_and_no_ai_calls(ai, client):
    ai(None)
    events = run_call(client, RULES_SCAM)
    assert not ai_evidence(events) and rule_evidence(events)
    assert sum(sessions_mod.AI_ANSWERS.values()) == 0


def test_health_shows_which_ai_answered(ai, client):
    ai(FakeAI(groq="answer"))
    run_call(client, SOFT_SCAM)
    h = client.get("/health").json()
    assert h["ai_answers"]["groq"] >= 1
