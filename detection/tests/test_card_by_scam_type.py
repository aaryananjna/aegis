"""The first card matches the scam: family caller -> code word, anyone else -> don't pay, call back."""
from pathlib import Path

import pytest

from hangup_detect.config import Config
from hangup_detect.counter import CARD_TEXT, CounterMoves
from hangup_detect.replay import parse_call, replay
from hangup_detect.rules import find_evidence
from hangup_detect.types import Tactic as T

ROOT = Path(__file__).resolve().parents[1]


def imp(text):
    return [e for e in find_evidence(text, "u", 0.0) if e.tactic == T.IMPERSONATION]


@pytest.mark.parametrize("text", ["Nana it's me, I'm in trouble", "Grandma, this is your grandson",
                                  "It's me, Grandma"])
def test_family_impersonation_is_tagged_family(text):
    (e,) = imp(text)
    assert e.detail == "family"


@pytest.mark.parametrize("text", ["I'm calling from the IRS about your taxes",
                                  "This is Microsoft support, your computer has a virus",
                                  "I'm with your bank's fraud department"])
def test_other_impersonation_is_tagged_official(text):
    (e,) = imp(text)
    assert e.detail == "official"


def test_evidence_dict_shape_unchanged():
    (e,) = imp("Nana it's me")
    assert set(e.as_dict()) == {"tactic", "quote", "span", "source"}


def test_family_caller_gets_codeword_cards():
    c = CounterMoves(Config())
    acts = c.update("high", .85, set(), set(), ["q"], 0.0, family=True)
    assert acts[0][1] == "codeword" and "code word" in acts[0][2]
    acts = c.update("high", .9, {T.VERIFICATION_AVOIDANCE}, set(), ["q"], 1.0, family=True)
    assert acts[0][1] == "hangup" and "saved number" in acts[0][2]


def test_other_caller_gets_verify_cards():
    c = CounterMoves(Config())
    acts = c.update("high", .85, set(), set(), ["q"], 0.0, family=False)
    assert acts[0][1] == "verify" and "code word" not in acts[0][2]
    assert acts[1][1] == "verify"  # alert kind matches the card
    acts = c.update("high", .9, {T.VERIFICATION_AVOIDANCE}, set(), ["q"], 1.0, family=False)
    assert acts[0][1] == "hangup" and "official" in acts[0][2]


def test_card_kind_is_decided_once():
    c = CounterMoves(Config())
    c.update("high", .85, set(), set(), ["q"], 0.0, family=False)
    acts = c.update("high", .9, {T.VERIFICATION_AVOIDANCE}, set(), ["q"], 1.0, family=True)
    assert "official" in acts[0][2]  # still the non-family hang up text


def cards(path):
    call = parse_call(path.read_text())
    return [(e["kind"], e["text"]) for e in replay(call) if e["type"] == "intervention"]


def test_grandson_scam_replay_asks_code_word():
    got = cards(ROOT / "examples" / "scam-grandson.call")
    assert [k for k, _ in got] == ["codeword", "hangup"]


def test_bank_scam_replay_does_not_ask_code_word():
    got = cards(ROOT / "eval" / "calls" / "dev" / "scam-bank-giftcards.call")
    assert got and got[0][0] == "verify"
    assert all("code word" not in text for _, text in got)


def test_every_card_kind_has_text():
    assert {"codeword", "verify", "hangup_family", "hangup_other"} <= set(CARD_TEXT)
