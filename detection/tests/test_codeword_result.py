"""C12 (contracts v2.1): the elder screen reports whether the caller gave the right code word."""
from hangup_detect.config import Config
from hangup_detect.counter import CounterMoves
from hangup_detect.pipeline import Detector
from hangup_detect.types import Tactic as T, make_segment

VA = {T.VERIFICATION_AVOIDANCE}


def at_codeword():
    c = CounterMoves(Config())
    c.update("high", 0.97, set(), set(), ["q"], 0.0, family=True)
    assert c.state == "codeword"
    return c


def test_wrong_answer_escalates_at_once():
    c = at_codeword()
    acts = c.codeword_result(False, ["q"], set(), 1.0)
    assert [(a[0], a[1]) for a in acts] == [("intervention", "hangup"), ("alert", "hangup")]
    assert "saved number" in acts[0][2]


def test_right_answer_stops_score_escalation():
    c = at_codeword()
    assert c.codeword_result(True, ["q"], set(), 1.0) == [("codeword_ok",)]
    # Score stays above 0.95 for a long time: no hang up card.
    assert c.update("high", 0.99, set(), set(), ["q"], 60.0, family=True) == []
    assert c.state == "codeword"


def test_right_answer_then_dodge_still_escalates():
    c = at_codeword()
    c.codeword_result(True, ["q"], set(), 1.0)
    acts = c.update("high", 0.9, VA, set(), ["q"], 5.0, family=True)
    assert acts[0][1] == "hangup"


def test_result_ignored_unless_codeword_card_is_up():
    c = CounterMoves(Config())
    assert c.codeword_result(False, ["q"], set(), 0.0) == []
    assert c.state == "none"
    v = CounterMoves(Config())
    v.update("high", 0.9, set(), set(), ["q"], 0.0, family=False)  # verify card, no code word
    assert v.codeword_result(False, ["q"], set(), 1.0) == []
    assert v.state == "verify"


SCAM = ["Nana it's me, I got in an accident",
        "Please don't tell Mom, I need Google Play gift cards right now"]


def detector_at_codeword():
    d = Detector(Config(), "s1")
    d.set_elder(None, 0.0)
    for i, line in enumerate(SCAM):
        d.feed(make_segment(f"u{i}", 0, "caller", line, i * 3, i * 3 + 1, True), i * 3 + 1.5)
    assert d.state()["intervention"] == "codeword"
    return d


def test_detector_wrong_answer_emits_card_and_alert():
    d = detector_at_codeword()
    evs = d.codeword_result(False, 5.0)
    assert [e["type"] for e in evs] == ["intervention", "alert"]
    assert evs[0]["kind"] == "hangup" and evs[1]["alert_id"] == "s1:hangup"


def test_detector_right_answer_no_hangup_over_time():
    d = detector_at_codeword()
    (ok,) = d.codeword_result(True, 5.0)
    assert ok["type"] == "codeword_ok"
    for t in range(6, 120):
        assert [e for e in d.tick(float(t)) if e["type"] == "intervention"] == []
    assert d.state()["intervention"] == "codeword"


def test_detector_result_out_of_place_gives_status_warning():
    d = Detector(Config(), "s1")
    (e,) = d.codeword_result(False, 1.0)
    assert e["type"] == "status" and "codeword_result" in e["warning"]


# Issue #10 (Aryan): "false" is a non-empty string, so bool("false") is True. Fail closed.
import pytest  # noqa: E402


@pytest.mark.parametrize("bad", ["false", "no", "true", 0, 1, None, [], "False"])
def test_codeword_result_rejects_anything_but_a_real_bool(bad):
    d = detector_at_codeword()
    with pytest.raises(TypeError):
        d.codeword_result(bad, 5.0)
    assert d.state()["intervention"] == "codeword"  # nothing changed


# Issue #10 follow-up (Aryan): tell the family page the code word was answered right.
def test_codeword_ok_event_shape():
    d = detector_at_codeword()
    (e,) = d.codeword_result(True, 5.0)
    assert set(e) == {"type", "session_id", "t", "seq", "resolves"}
    assert e["resolves"] == "s1:codeword"  # the alert it answers


def test_codeword_ok_only_once():
    d = detector_at_codeword()
    d.codeword_result(True, 5.0)
    assert d.codeword_result(True, 6.0) == []


def test_wrong_answer_after_right_still_hangs_up():
    d = detector_at_codeword()
    d.codeword_result(True, 5.0)
    evs = d.codeword_result(False, 6.0)
    assert [e["type"] for e in evs] == ["intervention", "alert"]
