"""Caption mistakes real speech-to-text makes: fillers inside phrases, split words."""
import pytest

from hangup_detect.rules import find_evidence
from hangup_detect.types import Tactic as T


def hits(text):
    return {e.tactic: e for e in find_evidence(text, "u", 0.0)}


@pytest.mark.parametrize("tactic,text", [
    (T.PAYMENT, "buy the gift um cards today"),
    (T.SECRECY, "please don't uh tell Mom"),
    (T.PAYMENT, "move your money to a uh safe account"),
    (T.URGENCY, "you need to do it right um now"),
    (T.VERIFICATION_AVOIDANCE, "there's um no time for that"),
])
def test_fillers_inside_phrases_still_match(tactic, text):
    assert tactic in hits(text)


def test_span_and_quote_point_at_the_original_words():
    text = "please don't uh tell Mom"
    e = hits(text)[T.SECRECY]
    assert text[e.span[0]:e.span[1]] == e.quote
    assert e.quote == "please don't uh tell Mom"


def test_filler_words_alone_do_nothing():
    assert hits("um uh erm hmm") == {}


def test_real_words_are_not_treated_as_fillers():
    # "like" and "so" carry meaning, so they stay
    assert T.PAYMENT not in hits("gift like cards")


@pytest.mark.parametrize("text", ["send it through the bit coin machine", "use a bitcoin ATM"])
def test_bitcoin_split_by_captions(text):
    assert T.PAYMENT in hits(text)
