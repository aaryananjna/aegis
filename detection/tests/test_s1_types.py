import math

import pytest

from hangup_detect import events
from hangup_detect.config import Config
from hangup_detect.types import Segment, Tactic, make_segment

COMMON = {"type", "session_id", "t", "seq"}


def test_eight_tactics():
    assert {t.value for t in Tactic} == {
        "impersonation", "urgency", "secrecy", "payment",
        "threat", "verification_avoidance", "remote_access", "distress",
    }


def test_tactic_set_shape():
    e = events.tactic_set("s1", 15.2, 31, "u7", 2, False,
                          [{"tactic": "secrecy", "quote": "don't tell Mom", "span": [24, 38], "source": "rule"}])
    assert COMMON | {"utterance_id", "revision", "provisional", "evidence"} == set(e)
    assert e["type"] == "tactic_set"


def test_risk_shape():
    e = events.risk("s1", 1.0, 2, 0.5, "elevated", {"rule": {}, "llm": {}, "combos": {}})
    assert COMMON | {"score", "level", "contributions"} == set(e)


def test_intervention_alert_status_shapes():
    i = events.intervention("s1", 1.0, 3, "codeword", "x")
    assert COMMON | {"kind", "text", "latched"} == set(i) and i["latched"] is True
    a = events.alert("s1", 1.0, 4, "codeword", ["q"], "sum")
    assert a["alert_id"] == "s1:codeword"
    assert COMMON | {"alert_id", "kind", "evidence", "summary"} == set(a)
    s = events.status("s1", 0.0, 1, "rules_only")
    assert COMMON | {"mode", "warning"} == set(s)


def test_default_config_is_valid():
    Config().validate()


@pytest.mark.parametrize("field,value", [
    ("half_life_s", 0), ("enter_high", 1.2), ("exit_high", 0.9),
    ("enter_elevated", 0.0), ("llm_cap", -1),
])
def test_bad_config_names_field(field, value):
    c = Config(**{field: value})
    with pytest.raises(ValueError, match=field):
        c.validate()


def test_negative_weight_rejected():
    c = Config()
    c.weights[Tactic.PAYMENT] = -1.0
    with pytest.raises(ValueError, match="weights"):
        c.validate()


def test_make_segment_cleans_input():
    s = make_segment("u1", 0, "nobody", "x" * 2500, 1.0, 2.0, True)
    assert s.speaker == "unknown"
    assert len(s.text) == 2000
    assert s.truncated is True


@pytest.mark.parametrize("start,end", [(math.nan, 1.0), (1.0, math.inf), (-1.0, 1.0), (2.0, 1.0)])
def test_make_segment_rejects_bad_times(start, end):
    with pytest.raises(ValueError):
        make_segment("u1", 0, "caller", "hi", start, end, True)


def test_segment_is_frozen():
    s = make_segment("u1", 0, "caller", "hi", 0.0, 1.0, True)
    with pytest.raises(Exception):
        s.text = "x"  # type: ignore[misc]
    assert isinstance(s, Segment)
