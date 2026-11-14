"""'Call the number on the back of your card' is the safe advice real banks give (and our own
hang up card). Reading the numbers off the back of a card to a caller is the scam."""
import pytest

from hangup_detect.rules import find_evidence
from hangup_detect.types import Tactic as T


def tactics(text):
    return {e.tactic for e in find_evidence(text, "u", 0.0)}


@pytest.mark.parametrize("text", [
    "If not please call the number on the back of your card",
    "Hang up and call the number on the back of your card.",
    "You can always dial the number on the back of the card",
    "call number on back of your card",  # messy caption
])
def test_calling_the_number_on_the_back_is_not_payment(text):
    assert T.PAYMENT not in tactics(text)


@pytest.mark.parametrize("text", [
    "Read me the numbers on the back",
    "Scratch the card and give me the codes on the back",
    "call me back with the codes from the back",
])
def test_reading_numbers_off_the_back_is_still_payment(text):
    assert T.PAYMENT in tactics(text)
