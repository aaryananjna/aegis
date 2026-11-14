import json
from pathlib import Path

import pytest

from hangup_detect.cli import parse_typed
from hangup_detect.replay import parse_call, replay

ROOT = Path(__file__).resolve().parents[1]
SCAM = ROOT / "examples" / "scam-grandson.call"
BENIGN = ROOT / "examples" / "benign-party.call"


def test_parse_headers_and_lines():
    call = parse_call(SCAM.read_text())
    assert call.headers["label"] == "scam" and call.headers["source"] == "synthetic"
    assert call.onset_s == 3.0
    first = call.lines[1]
    assert (first.start_s, first.end_s, first.speaker_raw, first.speaker) == (1.8, 4.6, "1", "unknown")


@pytest.mark.parametrize("bad,where", [
    ("# id: x\n# label: scam\n# source: synthetic\n[1.0] caller: hi\n", "line 4"),
    ("# id: x\n# label: scam\n# source: synthetic\n[2.0-1.0] caller: hi\n", "line 4"),
    ("# id: x\n# label: maybe\n# source: synthetic\n", "label"),
    ("# id: x\n# label: scam\n[0-1] caller: hi\n", "source"),
    ("# id: x\n# label: scam\n# source: synthetic\n[0-1] robot: hi\n", "line 4"),
])
def test_parse_errors_are_clear(bad, where):
    with pytest.raises(ValueError, match=where):
        parse_call(bad)


def test_caller_elder_labels():
    call = parse_call("# id: x\n# label: benign\n# source: synthetic\n[0-1] elder: hi\n[1-2] caller: yo\n")
    assert [l.speaker for l in call.lines] == ["elder", "caller"]


def test_scam_replay_hits_codeword_then_hangup():
    evs = replay(parse_call(SCAM.read_text()), elder="0")
    cards = [e["kind"] for e in evs if e["type"] == "intervention"]
    assert cards == ["codeword", "hangup"]
    assert len([e for e in evs if e["type"] == "alert"]) == 2


def test_benign_replay_stays_green():
    evs = replay(parse_call(BENIGN.read_text()), elder="0")
    assert all(e["level"] == "low" for e in evs if e["type"] == "risk")
    assert [e for e in evs if e["type"] in ("intervention", "alert")] == []


def test_replay_is_deterministic():
    call = parse_call(SCAM.read_text())
    assert json.dumps(replay(call, elder="0")) == json.dumps(replay(call, elder="0"))


def test_wrong_elder_scores_grandma_but_meter_only_before_confirm():
    evs = replay(parse_call(SCAM.read_text()), elder=None, confirm=False)
    assert [e for e in evs if e["type"] == "intervention"] == []


@pytest.mark.parametrize("name", ["scam-grandson", "benign-party"])
def test_fixtures_match_regeneration(name):
    path = ROOT / "fixtures" / f"events-{name}.jsonl"
    got = [json.loads(l) for l in path.read_text().splitlines()]
    assert got == replay(parse_call((ROOT / "examples" / f"{name}.call").read_text()), elder="0",
                         captions=True)


def test_parse_typed():
    assert parse_typed("c: gift cards") == ("caller", "gift cards")
    assert parse_typed("e: hello") == ("elder", "hello")
    assert parse_typed("nonsense") is None
