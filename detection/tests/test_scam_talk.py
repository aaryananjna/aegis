"""People talking ABOUT scams (warning, retelling) or about gift cards for a birthday must not
raise a warning. A scammer who talks about scams to sound safe must still be caught."""
from pathlib import Path

import pytest

from hangup_detect.replay import parse_call, replay
from hangup_detect.rules import Context, find_evidence
from hangup_detect.types import Tactic as T

DEV = Path(__file__).resolve().parents[1] / "eval" / "calls" / "dev"
TALK = Context(scam_talk=True)
GIFTS = Context(gift_occasion=True)


def tactics(text, ctx=None):
    return {e.tactic for e in find_evidence(text, "u", 0.0, ctx)}


def peak(name, no_speakers):
    evs = replay(parse_call((DEV / f"{name}.call").read_text()), no_speakers=no_speakers)
    levels = [e["level"] for e in evs if e["type"] == "risk"]
    cards = [e for e in evs if e["type"] == "intervention"]
    return ("high" if "high" in levels else "elevated" if "elevated" in levels else "low"), cards


@pytest.mark.parametrize("text", [
    "A woman called me pretending to be from my bank and wanted gift cards.",
    "There's a scam going around where people call pretending to be the bank and tell you to go buy gift cards.",
    "So if anyone calls and says gift cards or wire money, just hang up and call me.",
    "This man said he was from the IRS and I owed back taxes.",
    "A young man said Grandma it's me, I'm in trouble, I need bail money.",
    "Somebody called saying they were from Medicare and wanted her card number.",
])
def test_strong_frames_skip_reported_speech(text):
    assert tactics(text) == set()


def test_quote_continues_into_next_sentences_without_you():
    assert tactics("A young man said Grandma, it's me. I'm in trouble. I need bail money.") == set()


def test_weak_frames_only_count_once_the_call_is_about_scams():
    line = "He wanted me to go to the drugstore and buy gift cards."
    assert T.PAYMENT in tactics(line)
    assert tactics(line, TALK) == set()


def test_rhetorical_who_question():
    assert tactics("Who pays a bill with gift cards?") == set()


def test_echo_question_skipped_in_scam_talk():
    assert tactics("Gift cards?", TALK) == set()
    assert T.PAYMENT in tactics("Gift cards?")


def test_gift_cards_for_an_occasion():
    assert tactics("The boys just want gift cards.", GIFTS) == set()
    assert T.PAYMENT in tactics("Buy gift cards and read me the numbers on the back.", GIFTS)


@pytest.mark.parametrize("text", [
    "There's a scam on your account so you need to buy gift cards to protect it.",
    "Go to the store and buy gift cards, then read me the numbers.",
    "I know this sounds like a scam but it's not, I need bail money.",
    "They said I need bail money tonight.",
    "If they aren't fixed today your status gets cancelled and you could be deported.",
    "If he doesn't get bail tonight he stays in jail, so you need to wire the money.",
])
def test_direct_asks_still_count(text):
    assert tactics(text) != set()


def test_direct_ask_still_counts_in_scam_talk():
    assert T.PAYMENT in tactics("To protect you, you need to buy gift cards today.", TALK)


@pytest.mark.parametrize("name", ["benign-warns-medicare-callers", "benign-retells-fake-bank",
                                  "benign-elder-retells-grandkid", "benign-holiday-gift-cards"])
@pytest.mark.parametrize("no_speakers", [False, True])
def test_scam_talk_calls_stay_calm(name, no_speakers):
    level, cards = peak(name, no_speakers)
    assert level != "high" and not cards


@pytest.mark.parametrize("name", ["scam-bank-uses-scam-warning", "scam-grandson-not-a-scam"])
@pytest.mark.parametrize("no_speakers", [False, True])
def test_scammers_who_talk_about_scams_are_still_caught(name, no_speakers):
    assert peak(name, no_speakers)[0] == "high"
