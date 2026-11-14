"""Caption events in replays and fixtures, so C can build live captions without A's server."""
import json
from pathlib import Path

import pytest

from hangup_detect.replay import parse_call, replay

ROOT = Path(__file__).resolve().parents[1]
CAPTION_KEYS = {"type", "session_id", "t", "utterance_id", "revision", "speaker_raw",
                "text", "start_s", "end_s", "is_final"}


def scam():
    return parse_call((ROOT / "examples" / "scam-grandson.call").read_text())


def test_captions_off_by_default():
    assert not [e for e in replay(scam(), elder="0") if e["type"] == "caption"]


def test_one_caption_per_line_matching_the_contract():
    call = scam()
    caps = [e for e in replay(call, elder="0", captions=True) if e["type"] == "caption"]
    assert len(caps) == len(call.lines)
    for c, line in zip(caps, call.lines):
        assert set(c) == CAPTION_KEYS
        assert "seq" not in c  # seq orders B's events only (issue #1, point 5)
        assert c["text"] == line.text and c["speaker_raw"] == line.speaker_raw
        assert c["is_final"] is True


def test_caption_comes_before_its_highlights():
    evs = replay(scam(), elder="0", captions=True)
    seen = set()
    for e in evs:
        if e["type"] == "caption":
            seen.add(e["utterance_id"])
        if e["type"] == "tactic_set":
            assert e["utterance_id"] in seen


def test_highlight_spans_index_the_caption_text():
    evs = replay(scam(), elder="0", captions=True)
    text = {e["utterance_id"]: e["text"] for e in evs if e["type"] == "caption"}
    for e in evs:
        if e["type"] == "tactic_set":
            for x in e["evidence"]:
                assert text[e["utterance_id"]][x["span"][0]:x["span"][1]] == x["quote"]


def test_detector_events_unchanged_by_captions():
    a = replay(scam(), elder="0")
    b = [e for e in replay(scam(), elder="0", captions=True) if e["type"] != "caption"]
    assert a == b


@pytest.mark.parametrize("name", ["scam-grandson", "benign-party"])
def test_fixtures_include_captions(name):
    path = ROOT / "fixtures" / f"events-{name}.jsonl"
    got = [json.loads(l) for l in path.read_text().splitlines()]
    assert any(e["type"] == "caption" for e in got)
