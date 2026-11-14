import math

import pytest

from hangup_detect.config import Config
from hangup_detect.pipeline import Detector
from hangup_detect.types import make_segment


def seg(text, rev, final=False, speaker="caller", uid="u1"):
    return make_segment(uid, rev, speaker, text, 0.0, 1.0, final)


def sets(evs):
    return [e for e in evs if e["type"] == "tactic_set"]


def test_interim_highlights_without_scoring():
    d = Detector(Config(), "s1")
    evs = d.feed(seg("I need gift cards", 0), 1.0)
    (ts,) = sets(evs)
    assert ts["provisional"] is True and ts["evidence"][0]["tactic"] == "payment"
    assert d.risk.evidence == []
    assert [e for e in evs if e["type"] == "risk"] == []


def test_revision_replaces_and_final_clears():
    d = Detector(Config(), "s1")
    d.feed(seg("I need gift cards", 0), 1.0)
    (ts,) = sets(d.feed(seg("I need gift wrap", 1), 1.1))
    assert ts["provisional"] is True and ts["evidence"] == []
    assert sets(d.feed(seg("I need gift wrap for Mom", 2, final=True), 1.2)) == []


def test_final_that_drops_a_provisional_hit_clears_it():
    d = Detector(Config(), "s1")
    d.feed(seg("I need gift cards", 0), 1.0)
    (ts,) = sets(d.feed(seg("I need gift wrap", 1, final=True), 1.1))
    assert ts["provisional"] is False and ts["evidence"] == []


def test_final_scores_exactly_once():
    d = Detector(Config(), "s1")
    for r in range(3):
        d.feed(seg("I need gift cards", r), 1.0 + r * 0.1)
    (ts,) = sets(d.feed(seg("I need gift cards", 3, final=True), 1.5))
    assert ts["provisional"] is False
    assert len(d.risk.evidence) == 1
    assert d.risk.score(1.5) == pytest.approx(1 / (1 + math.exp(1.0)))


def test_elder_interim_has_no_highlights():
    d = Detector(Config(), "s1")
    assert d.feed(seg("I need gift cards", 0, speaker="elder"), 1.0) == []
