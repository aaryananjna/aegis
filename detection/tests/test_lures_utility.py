"""Gaps found from the recorded demo and a "free money" test (2026-11-15).

- A fake power company ("Valley Electric Dispatch") is an impersonation, like a bank.
- A stranger's money lure ("you won $10,000", "a grant") counts as impersonation, so a fee or a
  bank number asked for after it reaches a Warning on rules alone. The lure alone stays calm.
- The grandparent offering card numbers, and the caller asking for a receipt or card number,
  are payment evidence.
"""
import pytest

from hangup_detect.replay import parse_call, replay
from hangup_detect.rules import find_evidence
from hangup_detect.types import Tactic as T


def tactics(text):
    return {e.tactic for e in find_evidence(text, "u", 0.0)}


def call(*lines):
    body = "".join(f"[{i * 5.0:.1f}-{i * 5.0 + 4.0:.1f}] spk1: {t}\n" for i, t in enumerate(lines))
    return parse_call("# id: t\n# label: scam\n# source: synthetic\n# set: example\n" + body)


def run(*lines):
    evs = replay(call(*lines), no_speakers=True)
    return [e["level"] for e in evs if e["type"] == "risk"], [e for e in evs if e["type"] == "intervention"]


@pytest.mark.parametrize("text", [
    "This is Valley Electric Dispatch.",
    "Hi, I'm calling from the electric company about your account.",
    "This is Riverside Power and Light billing department.",
    "We're with the gas company.",
])
def test_utility_caller_is_impersonation(text):
    assert T.IMPERSONATION in tactics(text)


@pytest.mark.parametrize("text", [
    "I need to call the electric company about my bill tomorrow.",
    "The power company fixed the line on our street.",
])
def test_talking_about_a_utility_is_not(text):
    assert T.IMPERSONATION not in tactics(text)


@pytest.mark.parametrize("text", [
    "Congratulations, you have won 10,000 dollars in the national sweepstakes.",
    "You won $10,000.",
    "You've just won ten thousand dollars.",
    "I want to just give you 10,000 dollars for no reason, for free.",
    "You qualify for a government grant of 9,000 dollars.",
])
def test_money_lure_is_noticed(text):
    assert T.IMPERSONATION in tactics(text)


@pytest.mark.parametrize("text", [
    "You won the game three to one, nice job.",
    "Grandma, I'll give you 20 dollars for gas, it's free, don't worry about it.",
])
def test_everyday_wins_and_gifts_are_not_lures(text):
    assert T.IMPERSONATION not in tactics(text)


def test_lure_alone_stays_calm():
    lv, cards = run("I want to just give you 10,000 dollars for no reason, for free.")
    assert "high" not in lv and not cards


@pytest.mark.parametrize("ask", [
    "You just need to pay a 200 dollar processing fee first.",
    "I just need your bank account number to deposit it.",
])
def test_lure_then_ask_reaches_warning(ask):
    lv, cards = run("You won 10,000 dollars.", ask)
    assert "high" in lv and cards


@pytest.mark.parametrize("text", [
    "Well, let me give you my credit card right now then.",
    "Let me read you my card number.",
    "Hold on, let me get my debit card.",
])
def test_grandparent_offering_card_is_payment(text):
    assert T.PAYMENT in tactics(text)


@pytest.mark.parametrize("text", [
    "Read me the numbers on the receipt.",
    "Take a picture of the back of the card and text it to me.",
    "Tell me the claim code on the card.",
])
def test_asking_for_card_or_receipt_numbers_is_payment(text):
    assert T.PAYMENT in tactics(text)


def test_demo_call_warns_before_the_gift_card():
    """The recorded demo, rules only: Warning by the time grandma offers her card."""
    lines = [
        "Hello, this is Valley Electric Dispatch. Our technician is thirty minutes away from shutting off your power meter.",
        "Shutting it off? My bill is an automatic payment every month.",
        "Your bank rejected the last two payments when we upgraded our billing system.",
        "Well, let me give you my credit card right now then.",
    ]
    lv, cards = run(*lines)
    assert lv[1] in ("elevated", "high")  # Be careful on the first line
    assert "high" in lv and cards
