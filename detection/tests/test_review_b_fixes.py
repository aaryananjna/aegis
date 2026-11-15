"""Fixes from the deep detection review (Fable 5.2, 2026-11-14). Each was reproduced first."""
import json

import pytest

from hangup_detect.config import Config
from hangup_detect.pipeline import Detector
from hangup_detect.rules import find_evidence
from hangup_detect.types import make_segment


def ai(*h):
    return json.dumps({"tactics": [{"tactic": t, "utterance_id": u, "quote": q} for t, u, q in h]})


def run(lines, answers=None):
    answers = answers or {}
    d = Detector(Config(), "s1")
    d.set_elder(None, 0.0)
    best, levels = 0.0, set()
    for i, t in enumerate(lines):
        at = i * 4.0 + 3
        evs = d.feed(make_segment(f"u{i}", 0, "unknown", t, i * 4.0, at - 0.5, True), at)
        if i in answers:
            r = d.llm_request(at)
            assert r is not None
            evs += d.apply_llm(r.seq, answers[i], at + 0.6)
        for e in evs:
            if e["type"] == "risk":
                best, levels = max(best, e["score"]), levels | {e["level"]}
    for t in range(int(len(lines) * 4 + 3), int(len(lines) * 4 + 20)):
        for e in d.tick(float(t)):
            if e["type"] == "risk":
                best, levels = max(best, e["score"]), levels | {e["level"]}
    return best, levels


def test_grandparent_asking_is_this_a_scam_does_not_switch_detection_off():
    lines = ["Hello?", "Is this a scam?", "Grandma, it's me.", "I got arrested.", "I need bail money.",
             "Please don't tell Mom."]
    assert "high" in run(lines)[1]


def test_more_ai_flags_never_lower_the_score():
    lines = ["Hello?", "Hello, I am calling about your account security.", "We need to confirm the details on file."]
    two = ai(("impersonation", "u1", "calling about your account security"), ("payment", "u2", "confirm the details on file"))
    three = ai(("impersonation", "u1", "calling about your account security"), ("payment", "u2", "confirm the details on file"),
               ("verification_avoidance", "u2", "We need to confirm"))
    assert run(lines, {2: three})[0] >= run(lines, {2: two})[0]


def test_a_failed_ai_request_is_retried_without_a_new_line():
    d = Detector(Config(), "s1")
    d.set_elder(None, 0.0)
    d.feed(make_segment("u0", 0, "unknown", "Grandma I need bail money", 0, 2, True), 2.5)
    assert d.llm_request(2.5) is not None
    d.llm_status("rules_only", 3.0, "groq timed out")
    assert d.llm_request(12.0) is not None


def test_holiday_small_talk_early_does_not_hide_gift_cards_later():
    lines = ["Hello?", "Hope you had a nice holiday.", "Fine, thanks.", "Anyway.", "Okay.", "Sure.",
             "This is the IRS.", "You owe back taxes.", "Buy three Target gift cards right now."]
    assert "high" in run(lines)[1]


@pytest.mark.parametrize("text", [
    "Do not worry just wire the money.",
    "This is not a joke you will be arrested.",
    "You might think it's a scam but go buy gift cards and read me the numbers on the back.",
    "If anyone asks, say the gift cards are for your grandson.",
    "Somebody wants to steal your savings so move your money to a safe account.",
])
def test_a_scammers_own_framing_does_not_switch_the_rules_off(text):
    assert find_evidence(text, "u", 0.0) != []


@pytest.mark.parametrize("text", [
    "If anyone asks you for gift cards, hang up and call me.",
    "That's a scam, the IRS never calls.",
    "I would never buy gift cards for a stranger.",
    "Someone wanted me to buy gift cards.",
])
def test_real_warnings_and_negations_still_skip(text):
    assert find_evidence(text, "u", 0.0) == []
