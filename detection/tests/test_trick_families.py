"""Scam tricks said in everyday wording, not the textbook script. Each case is a trick family,
written fresh (not copied from any test call). Everyday lines must stay quiet."""
import pytest

from hangup_detect.rules import find_evidence
from hangup_detect.types import Tactic as T


def tactics(text):
    return {e.tactic for e in find_evidence(text, "u", 0.0)}


CAUGHT = [
    ("Go to the drugstore and pick up a Green Dot card for three hundred.", T.PAYMENT),
    ("Buy a reload pack and read me the number on the receipt.", T.PAYMENT),
    ("You'll need to mail a cashier's check to our office today.", T.PAYMENT),
    ("Send the money to our secure reversal account and it will bounce back.", T.PAYMENT),
    ("Our courier can pick up the cash from your door this afternoon.", T.PAYMENT),
    ("We need eight hundred in cash up front for the materials.", T.PAYMENT),
    ("Before we release the winnings you have to pay the processing fee.", T.PAYMENT),
    ("There is a bench warrant out for you as of this morning.", T.THREAT),
    ("If you go down there the deputies will arrest you on sight.", T.THREAT),
    ("We are shutting off your electricity within the hour.", T.THREAT),
    ("This is the card fraud prevention unit at your bank.", T.IMPERSONATION),
    ("Type in the remote connection code I give you.", T.REMOTE_ACCESS),
    ("Read me the letters and numbers on your insurance card.", T.REMOTE_ACCESS),
    ("Can you sit down at your computer for me?", T.REMOTE_ACCESS),
]


@pytest.mark.parametrize("text,tactic", CAUGHT)
def test_trick_family_is_caught(text, tactic):
    assert tactic in tactics(text)


QUIET = [
    "I bought a gift basket at the farmers market.",
    "The pharmacy says the copay is due when I pick it up.",
    "Wait, you don't want a processing fee, do you?",
    "We're collecting twenty dollars for the cake, bring cash to the party.",
    "Feel free to hang up and call the number on the back of your card.",
    "Our crew will shut off the water to fix the pipe.",
    "My card number? No, I won't give that out.",
    "I sat down at my computer and wrote to my grandson.",
    "The courier left the package with the guard.",
]


@pytest.mark.parametrize("text", QUIET)
def test_everyday_line_stays_quiet(text):
    assert not (tactics(text) & {T.PAYMENT, T.THREAT, T.REMOTE_ACCESS, T.IMPERSONATION})
