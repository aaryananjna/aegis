"""Captions sometimes drop small words ("stay on line"). The rules should still match.

Measured 2026-11-14 on the 21 dev calls: dropping 20% of only the small words cut rules-only
catches from 110/110 to 94/110. Content words ("gift", "safe") are the AI layer's job.
"""
import pytest

from hangup_detect.rules import find_evidence
from hangup_detect.types import Tactic as T

DROPPED = [
    ("stay on line", T.VERIFICATION_AVOIDANCE),
    ("you need to move money to protect it", T.PAYMENT),
    ("this is bank's fraud department", T.IMPERSONATION),
    ("read me the numbers on back", T.PAYMENT),
    ("keep money safe", T.PAYMENT),
    ("she's in hospital", T.DISTRESS),
    ("they will suspend benefits", T.THREAT),
    ("keep it secret", T.SECRECY),
    ("you dont need call anyone", T.VERIFICATION_AVOIDANCE),
    ("warrant for arrest", T.THREAT),
]


@pytest.mark.parametrize("text,tactic", DROPPED)
def test_rule_survives_a_dropped_small_word(text, tactic):
    assert tactic in {e.tactic for e in find_evidence(text, "u", 0.0)}


# Everyday lines that must stay quiet after loosening.
NORMAL = [
    "Did you get to the store today?",
    "I put the money for the pizza on the counter.",
    "The bank is closed on Sunday, I'll go Monday.",
    "We were in the hospital waiting room for an hour last year, all fine now.",
    "Can you read me the recipe on the back of the box?",
    "My neighbor said the power was out on Elm Street.",
    "I'm calling from the pharmacy, your prescription is ready.",
    "Keep the change, it's yours.",
    "Line up the chairs for the party.",
    "My lawyer said the papers are ready.",  # bare "lawyer" is not a claim to be one
    "The police officer at Dad's work was nice.",
    "I need help moving the couch on Saturday.",
    "We need to shut off water to fix the pipe.",
]


@pytest.mark.parametrize("text", NORMAL)
def test_everyday_lines_stay_quiet(text):
    assert find_evidence(text, "u", 0.0) == []
