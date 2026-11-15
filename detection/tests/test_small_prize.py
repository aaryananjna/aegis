"""A small real prize ("you won a $50 gift card to the diner, pick it up at the church office")
is not a lure (red team, 2026-11-15: a false Warning from #106's widened "you won"). Big money
from a stranger still is."""
from pathlib import Path

from hangup_detect.replay import parse_call, replay
from hangup_detect.rules import find_evidence
from hangup_detect.types import Tactic as T

RAFFLE = """# id: t
# label: benign
# source: synthetic
# set: example
[0.0-1.0] spk0: Hello?
[1.6-5.8] spk1: Dorothy, it's Ruth from church. You won the raffle on Sunday!
[6.4-7.9] spk0: I never win anything.
[8.5-12.3] spk1: Well you won a $50 gift card to Rosie's Diner.
[12.9-17.8] spk1: You can pick it up at the church office any time this week.
[18.4-20.3] spk0: How lovely. Thank you, Ruth.
"""


def test_small_prize_is_not_a_lure():
    assert T.IMPERSONATION not in {e.tactic for e in find_evidence("Well you won a $50 gift card to Rosie's Diner.", "u", 0.0)}


def test_church_raffle_stays_calm():
    for ns in (True, False):
        lv = [e["level"] for e in replay(parse_call(RAFFLE), no_speakers=ns) if e["type"] == "risk"]
        assert "high" not in lv


def test_big_money_is_still_a_lure():
    for text in ("You won $10,000.", "You won 10,000 dollars.", "You've just won ten thousand dollars."):
        assert T.IMPERSONATION in {e.tactic for e in find_evidence(text, "u", 0.0)}
