"""'I'll fax it right now' is the caller promising their own action, not rushing the listener."""
from pathlib import Path

import pytest

from hangup_detect.replay import parse_call, replay
from hangup_detect.rules import find_evidence
from hangup_detect.types import Tactic as T

DEV = Path(__file__).resolve().parents[1] / "eval" / "calls" / "dev"


def urgency(text):
    return [e for e in find_evidence(text, "u", 0.0) if e.tactic is T.URGENCY]


@pytest.mark.parametrize("text", [
    "Absolutely. I'll fax her office right now and call you back tomorrow.",
    "Sure, I'll email it right away.",
    "Let me check the time with Dr. Lee right now.",
    "I will send it over immediately.",
])
def test_own_promise_is_not_urgency(text):
    assert urgency(text) == []


@pytest.mark.parametrize("text", [
    "I need bail money right now.",
    "You need to pay this right now.",
    "Go to the store right away.",
    "I'll stay on the line, but you have to buy them right now.",
    "I will freeze your account immediately unless you pay.",
])
def test_rushing_the_listener_still_counts(text):
    assert urgency(text) != []


@pytest.mark.parametrize("no_speakers", [False, True])
def test_office_call_has_no_highlights(no_speakers):
    evs = replay(parse_call((DEV / "benign-office-will-call-right-back.call").read_text()), no_speakers=no_speakers)
    assert not [e for e in evs if e["type"] == "tactic_set" and e["evidence"]]
