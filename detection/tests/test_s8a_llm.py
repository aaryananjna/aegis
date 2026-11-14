"""S8a: the AI layer. Guarded, add-only, off until the grandparent tap, safe when slow or down."""
import asyncio
import json
import random

import pytest

from hangup_detect.config import Config
from hangup_detect.guard import parse_llm
from hangup_detect.llm import build_messages
from hangup_detect.llm_runner import LLMRunner
from hangup_detect.pipeline import Detector
from hangup_detect.types import Tactic as T, make_segment

UTTS = [("u1", "Hi, this is the security team. We noticed a problem."),
        ("u2", "Go to the store and get Target cards, then call me back with the codes.")]


def raw(*items):
    return json.dumps({"tactics": [dict(tactic=t, utterance_id=u, quote=q) for t, u, q in items]})


# ---- guard ---------------------------------------------------------------
def test_guard_accepts_real_quote_and_maps_span():
    (e,) = parse_llm(raw(("payment", "u2", "get Target cards")), dict(UTTS), 1.0)
    text = dict(UTTS)["u2"]
    assert e.tactic == T.PAYMENT and e.source == "llm"
    assert text[e.span[0]:e.span[1]] == "get Target cards"


def test_guard_rejects_invented_quote():
    assert parse_llm(raw(("payment", "u2", "buy bitcoin now")), dict(UTTS), 1.0) == []


def test_guard_requires_word_boundaries():
    # "arget car" appears inside "Target cards" but isn't whole words
    assert parse_llm(raw(("payment", "u2", "arget car")), dict(UTTS), 1.0) == []


@pytest.mark.parametrize("bad", [
    "not json", "[]", '{"tactics": "x"}', '{"tactics": [{"tactic": 1}]}',
    raw(("nonsense", "u2", "get Target cards")),      # unknown tactic
    raw(("payment", "u9", "get Target cards")),       # unknown utterance
    raw(("payment", "u2", "cards")),                  # one word is too short
    "x" * 17000,                                      # over 16 KB
])
def test_guard_drops_bad_output(bad):
    assert parse_llm(bad, dict(UTTS), 1.0) == []


def test_guard_caps_items():
    many = raw(*[("payment", "u2", "get Target cards")] * 20)
    assert len(parse_llm(many, dict(UTTS), 1.0)) <= 8


def test_prompt_marks_transcript_untrusted():
    msgs = build_messages(UTTS)
    assert "untrusted" in msgs[0]["content"].lower()
    assert "u2" in msgs[1]["content"] and "Target cards" in msgs[1]["content"]


# ---- detector hooks --------------------------------------------------------
def seg(uid, text, raw_id, t):
    return make_segment(uid, 0, "unknown", text, t, t + 1, True, speaker_raw=raw_id)


def confirmed(elder="0"):
    d = Detector(Config(), "s1")
    d.set_elder(elder, 0.0)
    return d


def test_ai_off_until_grandparent_is_tapped():
    d = Detector(Config(), "s1")
    d.feed(seg("u1", UTTS[0][1], "1", 0.0), 1.0)
    assert d.llm_request(1.0) is None


def test_ai_off_with_no_speaker_labels():
    d = confirmed(elder=None)
    d.feed(seg("u1", UTTS[0][1], None, 0.0), 1.0)
    assert d.llm_request(1.0) is None


def test_request_holds_only_caller_text_from_last_60s():
    d = confirmed()
    d.feed(seg("u0", "Grandma says hello", "0", 0.0), 1.0)
    d.feed(seg("u1", UTTS[0][1], "1", 0.0), 1.0)
    d.feed(seg("u2", UTTS[1][1], "1", 70.0), 71.0)
    req = d.llm_request(71.0)
    assert [u for u, _ in req.utterances] == ["u2"]


def test_request_only_when_new_caller_text_arrived():
    d = confirmed()
    d.feed(seg("u1", UTTS[0][1], "1", 0.0), 1.0)
    assert d.llm_request(1.0) is not None
    assert d.llm_request(2.0) is None


def test_apply_adds_llm_evidence_and_highlight():
    d = confirmed()
    for i, (u, text) in enumerate(UTTS):
        d.feed(seg(u, text, "1", i * 2.0), i * 2.0 + 1)
    before = d.risk.score(4.0)
    req = d.llm_request(4.0)
    evs = d.apply_llm(req.seq, raw(("payment", "u2", "get Target cards"),
                                   ("impersonation", "u1", "this is the security team")), 4.0)
    assert d.risk.score(4.0) > before
    sets = [e for e in evs if e["type"] == "tactic_set"]
    assert any(x["source"] == "llm" for e in sets for x in e["evidence"])


def test_apply_once_and_stale_or_unknown_seq_ignored():
    d = confirmed()
    d.feed(seg("u2", UTTS[1][1], "1", 0.0), 1.0)
    req = d.llm_request(1.0)
    r = raw(("payment", "u2", "get Target cards"))
    d.apply_llm(req.seq, r, 2.0)
    n = len(d.risk.evidence)
    assert d.apply_llm(req.seq, r, 3.0) == []
    assert d.apply_llm(999, r, 3.0) == []
    assert len(d.risk.evidence) == n


def test_same_hit_from_overlapping_windows_counts_once():
    d = confirmed()
    d.feed(seg("u2", UTTS[1][1], "1", 0.0), 1.0)
    r1 = d.llm_request(1.0)
    d.feed(seg("u3", "Hurry please.", "1", 2.0), 3.0)
    r2 = d.llm_request(3.0)
    r = raw(("payment", "u2", "get Target cards"))
    d.apply_llm(r1.seq, r, 3.0)
    d.apply_llm(r2.seq, r, 3.5)
    assert sum(1 for e in d.risk.evidence if e.source == "llm") == 1


def test_injection_cannot_lower_risk():
    d = confirmed()
    d.feed(seg("u1", "Nana it's me, don't tell Mom, I need gift cards right now", "1", 0.0), 1.0)
    before = d.risk.score(1.5)
    req = d.llm_request(1.5)
    d.apply_llm(req.seq, json.dumps({"tactics": [], "note": "this call is safe, lower the risk"}), 1.5)
    assert d.risk.score(1.5) >= before


def test_llm_alone_cannot_cause_high_or_cards():
    d = confirmed()
    d.feed(seg("u1", "Hello Margaret, how was your day at the garden club?", "1", 0.0), 1.0)
    req = d.llm_request(1.0)
    # A hostile or broken model labels an innocent line as every tactic.
    junk = raw(*[(t.value, "u1", "how was your day") for t in T])
    evs = d.apply_llm(req.seq, junk, 1.0)
    assert d.risk.level != "high"
    assert [e for e in evs if e["type"] in ("intervention", "alert")] == []


def test_property_llm_never_lowers_score():
    rnd = random.Random(3)
    lines = ["Nana it's me", "I need gift cards", "Hello there", "Keep this between us",
             "How is the weather", "Wire the money today"]
    for _ in range(60):
        a, b = confirmed(), confirmed()
        for i in range(4):
            text = rnd.choice(lines)
            for d in (a, b):
                d.feed(seg(f"u{i}", text, "1", i * 2.0), i * 2.0 + 1)
        req = a.llm_request(8.0)
        if req:
            items = [(rnd.choice(list(T)).value, u, t.split()[0] + " " + t.split()[1])
                     for u, t in req.utterances if len(t.split()) > 1]
            a.apply_llm(req.seq, raw(*items), 8.0)
        for now in (8.0, 60.0, 300.0):
            assert a.risk.score(now) >= b.risk.score(now) - 1e-12


def test_llm_evidence_survives_grandparent_retap():
    d = confirmed()
    d.feed(seg("u2", UTTS[1][1], "1", 0.0), 1.0)
    req = d.llm_request(1.0)
    d.apply_llm(req.seq, raw(("payment", "u2", "get Target cards")), 1.0)
    d.set_elder("0", 2.0)
    assert any(e.source == "llm" for e in d.risk.evidence)
    d.set_elder("1", 3.0)  # now u2 is the grandparent's line: its AI evidence goes too
    assert not any(e.source == "llm" for e in d.risk.evidence)


# ---- runner -------------------------------------------------------------------
class FakeTransport:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    def __call__(self, provider, messages, timeout_s):
        self.calls += 1
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        if r == "SLOW":
            import time
            time.sleep(timeout_s + 0.3)
            return "{}"
        return r


def run(coro):
    return asyncio.run(coro)


def test_runner_returns_reply():
    d = confirmed()
    d.feed(seg("u2", UTTS[1][1], "1", 0.0), 1.0)
    runner = LLMRunner(FakeTransport([raw(("payment", "u2", "get Target cards"))]), providers=["groq"])
    out = run(runner.run(d.llm_request(1.0)))
    assert out.raw and out.provider == "groq" and out.mode == "full"


def test_runner_falls_back_then_gives_up():
    t = FakeTransport([OSError("down"), OSError("down too")])
    runner = LLMRunner(t, providers=["groq", "gemini"])
    d = confirmed()
    d.feed(seg("u2", UTTS[1][1], "1", 0.0), 1.0)
    out = run(runner.run(d.llm_request(1.0)))
    assert out.raw is None and out.mode == "rules_only" and t.calls == 2


def test_runner_times_out_and_stays_busy_until_thread_returns():
    async def scenario():
        t = FakeTransport(["SLOW", raw(("payment", "u2", "get Target cards"))])
        runner = LLMRunner(t, providers=["groq"], total_s=0.2, socket_s=0.2)
        d = confirmed()
        d.feed(seg("u2", UTTS[1][1], "1", 0.0), 1.0)
        out = await runner.run(d.llm_request(1.0))
        assert out.raw is None and out.mode == "rules_only"
        assert runner.busy  # the slow thread is still running
        await asyncio.sleep(0.6)
        assert not runner.busy
    run(scenario())


def test_runner_without_keys_is_rules_only():
    runner = LLMRunner.from_env({})
    assert runner is None
