"""Deepgram results -> caption events (CONTRACTS: A -> B caption)."""
from aegis_server.stt.captions import CaptionMaker


def res(words, is_final=False):
    return {"type": "Results", "is_final": is_final,
            "channel": {"alternatives": [{"transcript": " ".join(w[0] for w in words),
                                          "words": [{"word": w[0].lower(), "punctuated_word": w[0],
                                                     "start": w[1], "end": w[2], "speaker": w[3]}
                                                    for w in words]}]}}


def test_interims_then_final_share_an_utterance_and_revisions_rise():
    m = CaptionMaker("s1")
    a = m.feed(res([("Nana", 0.1, 0.4, 0)]))
    b = m.feed(res([("Nana", 0.1, 0.4, 0), ("it's", 0.5, 0.7, 0)]))
    c = m.feed(res([("Nana", 0.1, 0.4, 0), ("it's", 0.5, 0.7, 0), ("me.", 0.8, 1.0, 0)], True))
    assert [x["utterance_id"] for x in a + b + c] == ["u0-0"] * 3
    assert [x["revision"] for x in a + b + c] == [1, 2, 3]
    assert [x["is_final"] for x in a + b + c] == [False, False, True]
    assert c[0]["text"] == "Nana it's me."
    assert c[0] | {} == {"type": "caption", "session_id": "s1", "utterance_id": "u0-0",
                         "revision": 3, "speaker_raw": "0", "text": "Nana it's me.",
                         "start_s": 0.1, "end_s": 1.0, "is_final": True, "source": "live"}
    nxt = m.feed(res([("Hello", 1.5, 1.8, 0)]))
    assert nxt[0]["utterance_id"] == "u1-0" and nxt[0]["revision"] == 1


def test_one_result_with_two_speakers_becomes_two_captions():
    m = CaptionMaker("s1")
    out = m.feed(res([("Grandma?", 0, 0.5, 0), ("Who", 0.7, 0.9, 1), ("is", 0.9, 1.0, 1),
                      ("this?", 1.0, 1.2, 1)], True))
    assert [(c["utterance_id"], c["speaker_raw"], c["text"]) for c in out] == [
        ("u0-0", "0", "Grandma?"), ("u0-1", "1", "Who is this?")]
    assert out[1]["start_s"] == 0.7 and out[1]["end_s"] == 1.2


def test_run_dropped_by_the_final_is_closed_empty():
    m = CaptionMaker("s1")
    m.feed(res([("hi", 0, 0.2, 0), ("there", 0.3, 0.5, 1)]))
    out = m.feed(res([("hi", 0, 0.2, 0), ("there", 0.3, 0.5, 0)], True))
    assert [(c["utterance_id"], c["text"], c["is_final"]) for c in out] == [
        ("u0-0", "hi there", True), ("u0-1", "", True)]


def test_empty_interims_are_skipped_and_empty_final_closes_lines():
    m = CaptionMaker("s1")
    assert m.feed(res([])) == []
    m.feed(res([("um", 0, 0.2, 0)]))
    out = m.feed(res([], True))
    assert [(c["utterance_id"], c["text"], c["is_final"]) for c in out] == [("u0-0", "", True)]


def test_no_speaker_labels_gives_null_speaker_raw():
    m = CaptionMaker("s1")
    out = m.feed(res([("hello", 0, 0.3, None)], True))
    assert out[0]["speaker_raw"] is None


def test_other_messages_ignored():
    m = CaptionMaker("s1")
    assert m.feed({"type": "Metadata"}) == [] and m.feed({"type": "SpeechStarted"}) == []


def test_reconnect_offset_and_close_open():
    m = CaptionMaker("s1")
    m.feed(res([("wait", 0, 0.3, 0)]))
    closed = m.close_open()
    assert closed[0]["is_final"] and closed[0]["revision"] == 2
    m.offset_s = 30.0
    out = m.feed(res([("again", 0.2, 0.5, 0)], True))
    assert out[0]["utterance_id"] == "u1-0" and out[0]["start_s"] == 30.2
