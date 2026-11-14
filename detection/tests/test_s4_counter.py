from hangup_detect.config import Config
from hangup_detect.counter import CounterMoves, summary
from hangup_detect.types import Tactic as T

CFG = Config()
VA = {T.VERIFICATION_AVOIDANCE}


def cm():
    return CounterMoves(CFG)


def test_first_high_shows_codeword_and_alerts():
    c = cm()
    acts = c.update("high", 0.85, set(), {T.PAYMENT}, ["gift cards"], 0.0)
    assert [a[0] for a in acts] == ["intervention", "alert"]
    assert acts[0][1] == "codeword" and "code word" in acts[0][2]
    assert acts[1][1] == "codeword" and acts[1][2] == ["gift cards"]
    assert c.state == "codeword"


def test_nothing_below_high():
    c = cm()
    assert c.update("elevated", 0.7, set(), {T.PAYMENT}, ["x"], 0.0) == []
    assert c.state == "none"


def test_dodge_after_codeword_escalates_at_once():
    c = cm()
    c.update("high", 0.85, set(), {T.PAYMENT}, ["q"], 0.0)
    acts = c.update("high", 0.86, VA, {T.PAYMENT}, ["q"], 1.0)
    assert [(a[0], a[1]) for a in acts] == [("intervention", "hangup"), ("alert", "hangup")]


def test_dodge_before_codeword_does_not_skip_ahead():
    c = cm()
    acts = c.update("high", 0.85, VA, {T.PAYMENT}, ["q"], 0.0)
    assert c.state == "codeword"
    assert [a[1] for a in acts] == ["codeword", "codeword"]


def test_very_high_score_waits_for_codeword_time():
    c = cm()
    c.update("high", 0.97, set(), set(), [], 0.0)
    assert c.update("high", 0.97, set(), set(), [], 19.9) == []
    assert c.state == "codeword"
    c.update("high", 0.97, set(), set(), [], 20.0)
    assert c.state == "hangup"


def test_never_goes_backwards_and_two_alerts_max():
    c = cm()
    alerts = []
    for i, (lvl, s, new) in enumerate([("high", .85, set()), ("high", .9, VA),
                                       ("low", .1, set()), ("high", .99, VA)]):
        alerts += [a for a in c.update(lvl, s, new, set(), ["q"], float(i)) if a[0] == "alert"]
    assert c.state == "hangup"
    assert [a[1] for a in alerts] == ["codeword", "hangup"]


def test_evidence_capped_at_three():
    c = cm()
    acts = c.update("high", .85, set(), set(), ["a", "b", "c", "d"], 0.0)
    assert acts[1][2] == ["a", "b", "c"]


def test_summary_plain_no_oxford_comma():
    s = summary({T.IMPERSONATION, T.SECRECY, T.PAYMENT})
    assert s == ("Caller claimed to be someone you know or an official, "
                 "asked for secrecy and asked to pay or move money in an unusual way.")
    assert summary({T.PAYMENT}) == "Caller asked to pay or move money in an unusual way."
    assert summary(set()) == "Caller showed signs of a scam."
