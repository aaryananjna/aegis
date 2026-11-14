import time

import pytest

from hangup_detect.rules import find_evidence
from hangup_detect.types import Tactic as T

CASES = {
    T.IMPERSONATION: (
        ["Nana it's me, I got in an accident",
         "Grandma, this is your grandson",
         "This is Officer Daniels from the police department",
         "I'm calling from the IRS about your taxes",
         "This is Microsoft support, your computer has a virus",
         "I'm with your bank's fraud department"],
        ["Hey Grandma, it's me, Ryan, how was your week?",
         "The police officer at Dad's work was nice",
         "I bought an Apple watch yesterday",
         "My Medicare card came in the mail"],
    ),
    T.URGENCY: (
        ["You need to do this right now",
         "There's no time, please hurry",
         "It has to be done within the hour"],
        ["No rush at all, call me whenever",
         "I went to urgent care for my ankle",
         "We'll talk next week"],
    ),
    T.SECRECY: (
        ["Please don't tell Mom about this",
         "Keep this between us, okay?",
         "Don't tell anyone, not even your bank"],
        ["Don't tell Mom about the party",
         "It's a surprise so don't tell anyone",
         "You can tell anyone you want"],
    ),
    T.PAYMENT: (
        ["Go to the store and buy Google Play gift cards",
         "Read me the numbers on the back",
         "Send it through the bitcoin ATM",
         "I need bail money tonight"],
        ["Your prescription payment is due Friday",
         "I paid the electric bill online",
         "I'm not asking for gift cards",
         "They said buy gift cards, that's a scam"],
    ),
    T.THREAT: (
        ["There is a warrant for your arrest",
         "You will be arrested if you don't pay",
         "We will shut off your power in one hour",
         "If you don't do it now, your benefits will be frozen",
         "Everyone has to switch or lose coverage"],
        ["We watched a prison movie last night",
         "Your account balance looks fine",
         "The lawyer said the will is ready"],
    ),
    T.VERIFICATION_AVOIDANCE: (
        ["Grandma there's no time for that",
         "Don't ask questions, just trust me",
         "Stay on the line and do not hang up"],
        ["Take your time, no rush",
         "You can call me back anytime",
         "Let me explain how the recipe works"],
    ),
    T.REMOTE_ACCESS: (
        ["Download AnyDesk so I can fix it",
         "I need remote access to your computer",
         "Let me take control of your computer"],
        ["I fixed my computer myself",
         "The remote control for the TV is broken",
         "The screen is too small to read"],
    ),
    T.DISTRESS: (
        ["I'm so scared, please help me",
         "I was in a car accident",
         "I broke my nose and I'm in trouble"],
        ["The movie was scary",
         "I helped Dad with the yard",
         "The hospital parking was easy"],
    ),
}


def tactics(text):
    return {e.tactic for e in find_evidence(text, "u1", 0.0)}


@pytest.mark.parametrize("tactic,text", [(t, s) for t, (pos, _) in CASES.items() for s in pos])
def test_positive(tactic, text):
    assert tactic in tactics(text)


@pytest.mark.parametrize("tactic,text", [(t, s) for t, (_, neg) in CASES.items() for s in neg])
def test_negative(tactic, text):
    assert tactic not in tactics(text)


def test_span_points_into_original_text():
    text = "Please don't tell Mom about this"
    (e,) = [e for e in find_evidence(text, "u9", 3.0) if e.tactic == T.SECRECY]
    assert text[e.span[0]:e.span[1]] == e.quote
    assert (e.utterance_id, e.source, e.t_s) == ("u9", "rule", 3.0)


def test_one_evidence_per_tactic_per_utterance():
    ev = find_evidence("buy gift cards, more gift cards, bitcoin too", "u1", 0.0)
    assert [e.tactic for e in ev].count(T.PAYMENT) == 1


def test_full_scam_line_hits_several():
    got = tactics("Nana it's me, don't tell Mom, I need gift cards right now")
    assert {T.IMPERSONATION, T.SECRECY, T.PAYMENT, T.URGENCY} <= got


def test_speed():
    lines = [s for pos, neg in CASES.values() for s in pos + neg] * 30
    start = time.perf_counter()
    for s in lines[:1000]:
        find_evidence(s, "u", 0.0)
    assert (time.perf_counter() - start) / 1000 < 0.005
