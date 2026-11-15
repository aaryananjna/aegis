"""Live rehearsal (2026-11-14 ~10:15 PM): a bank "reverse transfer" scam only reached a Warning
via the AI, ~25 s after the scam was obvious. Two suspicious things (a bank claiming fraud plus
"someone just tried to take money from your account") should be enough; a real bank that says
it blocked the charge must stay calm."""
from pathlib import Path

import pytest

from hangup_detect.replay import parse_call, replay
from hangup_detect.rules import find_evidence

DEV = Path(__file__).resolve().parents[1] / "eval" / "calls" / "dev"


def run(name, no_speakers):
    evs = replay(parse_call((DEV / f"{name}.call").read_text()), no_speakers=no_speakers)
    high = next((e["t"] for e in evs if e["type"] == "risk" and e["level"] == "high"), None)
    return high, [e for e in evs if e["type"] == "intervention"], [e["level"] for e in evs if e["type"] == "risk"]


@pytest.mark.parametrize("no_speakers", [False, True])
def test_two_suspicious_things_say_be_careful_and_the_ask_warns(no_speakers):
    evs = replay(parse_call((DEV / "scam-bank-reverse-transfer.call").read_text()), no_speakers=no_speakers)
    first = {}
    for e in evs:
        if e["type"] == "risk":
            first.setdefault(e["level"], e["t"])
    # the bank claim (ends 7 s) plus the account scare (ends 11 s): "Be careful" right away
    assert first.get("elevated", 99) <= 12.0
    # the money ask (the reverse transfer line ends 19 s): Warning
    assert first.get("high", 99) <= 19.6


@pytest.mark.parametrize("no_speakers", [False, True])
def test_real_bank_that_blocked_the_charge_stays_calm(no_speakers):
    high, cards, _ = run("benign-real-bank-blocked-charge", no_speakers)
    assert high is None and not cards


@pytest.mark.parametrize("text", [
    "Someone in Miami just tried to send $900 from your checking account using our transfer app.",
    "A man in Ohio just attempted to withdraw twelve hundred dollars from your savings.",
])
def test_fake_account_scare_is_a_threat(text):
    assert "threat" in {e.tactic.value for e in find_evidence(text, "u", 0.0)}


@pytest.mark.parametrize("text", [
    "You have to initiate a reverse transfer yourself.",
    "To stop it you need to do a reverse transfer yourself from your banking app.",
])
def test_reverse_it_yourself_is_payment(text):
    assert "payment" in {e.tactic.value for e in find_evidence(text, "u", 0.0)}


def test_a_blocked_charge_is_not_a_scare():
    assert find_evidence("Someone tried to use your debit card at a store in Ohio and we blocked it.", "u", 0.0) == []


@pytest.mark.parametrize("text", ["I never play games online. Do you need my card number?",
                                  "Do you need my account number?"])
def test_grandparent_offering_a_number_is_not_the_caller_asking(text):
    assert find_evidence(text, "u", 0.0) == []


@pytest.mark.parametrize("text", ["My bank's fraud department called me.",
                                  "Her bank's security team sent a letter."])
def test_someones_own_bank_is_not_impersonation(text):
    assert find_evidence(text, "u", 0.0) == []


def test_your_bank_still_is():
    assert find_evidence("This is your bank's fraud department.", "u", 0.0) != []
