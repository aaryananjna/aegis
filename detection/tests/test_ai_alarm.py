"""Switches for unscripted speech: the AI may raise the alarm itself (ai_alarm_tactics) and, with
labels off, read the call from the first line (llm_mixed_always). Both off by default."""
import json

from hangup_detect.config import Config
from hangup_detect.pipeline import Detector
from hangup_detect.types import make_segment

LINES = [("u0", "Hello?"),
         ("u1", "Your file shows you qualify for a free brace through your benefits this month."),
         ("u2", "I just need you to read off the letters and numbers on your benefits card.")]


def run(cfg, answer):
    d = Detector(cfg, "s1")
    d.set_elder(None, 0.0)
    evs = []
    for i, (u, t) in enumerate(LINES):
        evs += d.feed(make_segment(u, 0, "unknown", t, i * 3.0, i * 3 + 2, True, speaker_raw=None), i * 3 + 2.5)
    req = d.llm_request(9.0)
    if req is not None:
        evs += d.apply_llm(req.seq, json.dumps({"tactics": answer}), 9.0)
    evs += d.tick(10.0)
    return d, req, evs


TWO = [{"tactic": "impersonation", "utterance_id": "u1", "quote": "qualify for a free brace"},
       {"tactic": "remote_access", "utterance_id": "u2", "quote": "read off the letters and numbers"}]
ONE = TWO[:1]


def test_old_settings_ai_waits_for_a_rule_and_cannot_alarm():
    d, req, evs = run(Config(llm_mixed_always=False, ai_alarm_tactics=0), TWO)
    assert req is None  # no rule fired, so nothing was sent
    assert d.risk.level != "high"


def test_always_on_sends_from_the_first_lines():
    d, req, _ = run(Config(llm_mixed_always=True), TWO)
    assert req is not None and req.mixed


def test_two_ai_tactics_can_raise_the_alarm_when_switched_on():
    d, _, evs = run(Config(llm_mixed_always=True, ai_alarm_tactics=2), TWO)
    assert d.risk.level == "high"
    assert [e["kind"] for e in evs if e["type"] == "intervention"] == ["verify"]


def test_one_ai_tactic_is_not_enough():
    d, _, evs = run(Config(llm_mixed_always=True, ai_alarm_tactics=2), ONE)
    assert d.risk.level != "high"
    assert not [e for e in evs if e["type"] == "intervention"]


def test_switch_off_keeps_the_old_cap():
    d, _, _ = run(Config(llm_mixed_always=True, ai_alarm_tactics=0), TWO)
    assert d.risk.level != "high"


def test_demo_defaults_are_on():
    cfg = Config()
    assert cfg.llm_mixed_always and cfg.ai_alarm_tactics == 2
    d, req, evs = run(cfg, TWO)
    assert req is not None and d.risk.level == "high"
