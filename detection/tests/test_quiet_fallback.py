"""The AI layer failing must never show on a screen, and a Groq timeout hands over to Gemini."""
import asyncio
import time

from hangup_detect.config import Config
from hangup_detect.llm_runner import LLMRunner
from hangup_detect.pipeline import Detector


def det():
    d = Detector(Config(), "s1")
    d.set_elder(None, 0.0)
    return d


def test_ai_errors_never_reach_the_screens():
    d = det()
    evs = d.llm_status("full", 0.0)
    for i in range(1, 6):
        evs += d.llm_status("rules_only", float(i), "groq timed out")
    assert [e["mode"] for e in evs] == ["full", "rules_only"]
    assert all(e.get("warning") is None for e in evs)


def test_one_failure_does_not_flip_to_rules_only():
    d = det()
    d.llm_status("full", 0.0)
    assert d.llm_status("rules_only", 8.0, "groq timed out") == []
    assert d.llm_status("full", 16.0) == []  # still full, nothing to announce


def test_three_failures_in_a_row_switch_to_rules_only_and_success_switches_back():
    d = det()
    assert [e["mode"] for e in d.llm_status("full", 0.0)] == ["full"]
    out = []
    for t in (8.0, 16.0, 24.0):
        out += d.llm_status("rules_only", t, "groq timed out")
    assert [e["mode"] for e in out] == ["rules_only"]
    back = d.llm_status("full", 32.0)
    assert [e["mode"] for e in back] == ["full"]


class Transport:
    def __init__(self, groq):
        self.groq = groq
        self.calls = []

    def __call__(self, provider, messages, timeout_s):
        self.calls.append(provider)
        if provider == "groq" and self.groq == "slow":
            time.sleep(timeout_s + 0.2)
            return "{}"
        return '{"tactics": []}'


def _req():
    d = det()
    from hangup_detect.types import make_segment
    d.feed(make_segment("u1", 0, "unknown", "this is your bank, buy gift cards", 0, 2, True), 2.5)
    return d.llm_request(3.0)


def test_groq_timeout_hands_over_to_gemini():
    async def go():
        t = Transport("slow")
        r = LLMRunner(t, providers=["groq", "gemini"], total_s=0.8, socket_s=0.3)
        out = await r.run(_req())
        assert t.calls == ["groq", "gemini"]
        assert out.provider == "gemini" and out.mode == "full"
        await asyncio.sleep(0.6)
        assert not r.busy  # the slow Groq thread finished and is no longer tracked
    asyncio.run(go())


def test_default_budget_leaves_gemini_time_after_a_groq_timeout():
    r = LLMRunner(Transport("ok"), providers=["groq", "gemini"])
    assert r.total_s - r.socket_s >= 1.0
