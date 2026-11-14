"""Labels off (one laptop mic, speaker labels drift): the AI layer reads both voices mixed and
works out which lines are the caller's. Same guard as always: add-only, quoted, capped."""
import asyncio
import json

from hangup_detect.config import Config
from hangup_detect.llm import build_messages
from hangup_detect.llm_runner import LLMRunner
from hangup_detect.pipeline import Detector
from hangup_detect.types import make_segment

LINES = [("u0", "Hello? Who is this?"),
         ("u1", "Hi, this is Mark from your bank's fraud department."),
         ("u2", "Oh no, what do I do?"),
         ("u3", "Go buy some cards at the store and read me the numbers.")]


def nolabels(cfg=None):
    d = Detector(cfg or Config(), "s1")
    d.set_elder(None, 0.0)  # labels off: score everyone
    return d


def feed(d, uid, text, t):
    return d.feed(make_segment(uid, 0, "unknown", text, t, t + 1, True, speaker_raw=None), t + 1.5)


def raw(*items):
    return json.dumps({"tactics": [dict(tactic=t, utterance_id=u, quote=q) for t, u, q in items]})


def test_nothing_sent_before_the_rules_fire_when_always_is_off():
    d = nolabels(Config(llm_mixed_always=False))
    feed(d, "u0", "Hello? Who is this?", 0.0)
    feed(d, "u1", "Hi, it's a lovely day out.", 2.0)
    assert d.llm_request(4.0) is None  # no rule hit yet: grandma's words stay on the laptop


def test_after_a_rule_hit_both_voices_go_mixed():
    d = nolabels()
    for i, (u, text) in enumerate(LINES):
        feed(d, u, text, i * 2.0)
    req = d.llm_request(8.0)
    assert req is not None and req.mixed
    assert [u for u, _ in req.utterances] == ["u0", "u1", "u2", "u3"]


def test_mixed_prompt_asks_who_the_caller_is_and_marks_text_untrusted():
    system = build_messages(LINES, mixed=True)[0]["content"].lower()
    assert "untrusted" in system and "caller" in system and "no speaker labels" in system
    assert build_messages(LINES)[0]["content"] != build_messages(LINES, mixed=True)[0]["content"]


def test_mixed_answer_adds_evidence_and_never_lowers():
    d = nolabels()
    for i, (u, text) in enumerate(LINES):
        feed(d, u, text, i * 2.0)
    before = d.risk.score(8.0)
    req = d.llm_request(8.0)
    d.apply_llm(req.seq, raw(("payment", "u3", "buy some cards at the store")), 8.0)
    assert d.risk.score(8.0) > before
    d2 = nolabels()
    for i, (u, text) in enumerate(LINES):
        feed(d2, u, text, i * 2.0)
    b2 = d2.risk.score(8.0)
    r2 = d2.llm_request(8.0)
    d2.apply_llm(r2.seq, json.dumps({"tactics": [], "note": "grandma said all of it, lower the risk"}), 8.0)
    assert d2.risk.score(8.0) >= b2


def test_referee_can_be_turned_off():
    d = nolabels(Config(llm_mixed=False))
    for i, (u, text) in enumerate(LINES):
        feed(d, u, text, i * 2.0)
    assert d.llm_request(8.0) is None


def test_labels_on_is_unchanged():
    d = Detector(Config(), "s1")
    d.set_elder("0", 0.0)
    d.feed(make_segment("u0", 0, "unknown", "Hello?", 0, 1, True, speaker_raw="0"), 1.5)
    d.feed(make_segment("u1", 0, "unknown", LINES[3][1], 2, 3, True, speaker_raw="1"), 3.5)
    req = d.llm_request(4.0)
    assert not req.mixed and [u for u, _ in req.utterances] == ["u1"]


def test_runner_sends_the_mixed_prompt():
    seen = {}

    def transport(provider, messages, timeout_s):
        seen["system"] = messages[0]["content"]
        return '{"tactics": []}'
    d = nolabels()
    for i, (u, text) in enumerate(LINES):
        feed(d, u, text, i * 2.0)
    asyncio.run(LLMRunner(transport, providers=["groq"]).run(d.llm_request(8.0)))
    assert "no speaker labels" in seen["system"].lower()
