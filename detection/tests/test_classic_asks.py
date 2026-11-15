"""Plainly worded classic scams (card number, SSN/PIN, one-time code, virus + install, prize
taxes, kidnapping, money for a lawyer) must reach a Warning on rules alone, and their honest
look-alikes (a real bank that never asks for your PIN, a grandson's Zoom install, a church
raffle, a doctor's office, a grandparent questioning the caller) must not."""
from pathlib import Path

import pytest

from hangup_detect.replay import parse_call, replay

DEV = Path(__file__).resolve().parents[1] / "eval" / "calls" / "dev"
SCAMS = ["scam-card-number-billing", "scam-ssn-pin-security", "scam-virus-install", "scam-sweepstakes-taxes",
         "scam-kidnap-grandson", "scam-grandkid-attorney", "scam-otp-readback", "scam-ransom-or-else"]
NORMAL = ["benign-real-bank-never-asks", "benign-grandson-zoom-install", "benign-church-raffle-quilt",
          "benign-doctor-bring-cards", "benign-elder-questions-caller", "benign-friends-discuss-prize-email"]


def levels(name, no_speakers):
    evs = replay(parse_call((DEV / f"{name}.call").read_text()), no_speakers=no_speakers)
    return [e["level"] for e in evs if e["type"] == "risk"], [e for e in evs if e["type"] == "intervention"]


@pytest.mark.parametrize("no_speakers", [False, True])
@pytest.mark.parametrize("name", SCAMS)
def test_classic_scams_reach_a_warning(name, no_speakers):
    lv, _ = levels(name, no_speakers)
    assert "high" in lv


@pytest.mark.parametrize("no_speakers", [False, True])
@pytest.mark.parametrize("name", NORMAL)
def test_look_alikes_stay_calm(name, no_speakers):
    lv, cards = levels(name, no_speakers)
    assert "high" not in lv and not cards


from hangup_detect.rules import find_evidence  # noqa: E402


@pytest.mark.parametrize("text", [
    "Are you from the bank's fraud department?",
    "Do you want gift cards?",
    "Is there a warrant out for you or something?",
    "Did you say gift cards?",
])
def test_questioning_the_caller_is_not_evidence(text):
    assert find_evidence(text, "u", 0.0) == []


@pytest.mark.parametrize("text", [
    "Are you near a store that sells gift cards?",
    "Do you have your social security number handy?",
    "Is there a Walgreens near you where you can buy gift cards?",
    "Can you read that code back to me?",
])
def test_a_scammers_questions_still_count(text):
    assert find_evidence(text, "u", 0.0) != []


@pytest.mark.parametrize("text", [
    "You'll need to set a new pin when you come in.",
    "Please reset your password at the branch.",
    "Bring your social security card when you come in.",
])
def test_setting_your_own_pin_or_doing_it_in_person_is_not_an_ask(text):
    assert [e for e in find_evidence(text, "u", 0.0) if e.tactic.value == "payment"] == []


def test_giving_the_pin_to_the_caller_still_counts():
    assert find_evidence("I just need you to tell me your new pin.", "u", 0.0) != []
