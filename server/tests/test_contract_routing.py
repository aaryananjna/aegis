"""Who receives what, in which order, and replay on (re)connect (CONTRACTS v2.1: C1, C4, C6)."""
import pytest

from helpers import (DETECTOR_TYPES, FAMILY_TYPES, SCAM, SCAM_UNTIL_CODEWORD, drain, is_type,
                     recv, recv_until, send_call)

pytestmark = pytest.mark.xfail(strict=False, reason="not implemented yet")

SENT_CAPTION_FIELDS = ("utterance_id", "revision", "speaker_raw", "text", "start_s", "end_s",
                       "is_final", "source")


def play_full_scam(client, call, *listeners):
    """Send the whole grandson scam, end the call, and return what each listener received."""
    with client.websocket_connect(call.captions_url) as cap:
        send_call(cap, call, SCAM)
        cap.send_json({"type": "end"})
        return [recv_until(ws, is_type("call_ended")) for ws in listeners]


def test_elder_gets_every_event_including_captions(client, new_call):
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder:
        (seen,) = play_full_scam(client, call, elder)
    types = {e["type"] for e in seen}
    assert {"caption", "tactic_set", "risk", "intervention", "alert", "call_ended"} <= types
    kinds = [e["kind"] for e in seen if e["type"] == "intervention"]
    assert kinds == ["codeword", "hangup"]


def test_captions_reach_elder_unchanged_plus_t(client, new_call):
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder:
        (seen,) = play_full_scam(client, call, elder)
    captions = [e for e in seen if e["type"] == "caption"]
    assert len(captions) == len(SCAM)
    for sent, got in zip(SCAM, captions):
        assert {k: got[k] for k in SENT_CAPTION_FIELDS} == {k: sent[k] for k in SENT_CAPTION_FIELDS}
        assert got["session_id"] == call.id
        assert isinstance(got["t"], (int, float))
        assert "seq" not in got  # seq only orders the detector's events


def test_caption_arrives_before_its_tactic_set(client, new_call):
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder:
        (seen,) = play_full_scam(client, call, elder)
    tactic_sets = [e for e in seen if e["type"] == "tactic_set" and e["evidence"]]
    assert tactic_sets, "the scam call should highlight something"
    for ts in tactic_sets:
        key = (ts["utterance_id"], ts["revision"])
        caption_at = next(i for i, e in enumerate(seen) if e["type"] == "caption"
                          and (e["utterance_id"], e["revision"]) == key)
        assert caption_at < seen.index(ts)
        text = seen[caption_at]["text"]
        for ev in ts["evidence"]:
            start, end = ev["span"]
            assert text[start:end] == ev["quote"]  # span points into text the screen has


def test_detector_events_keep_seq_order(client, new_call):
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder:
        (seen,) = play_full_scam(client, call, elder)
    seqs = [e["seq"] for e in seen if "seq" in e]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
    assert all("seq" in e for e in seen if e["type"] in DETECTOR_TYPES - {"status"})


def test_family_gets_only_alert_intervention_codeword_ok_status_call_ended(client, new_call):
    call = new_call()
    with client.websocket_connect(call.events_url("family")) as family:
        (seen,) = play_full_scam(client, call, family)
    assert {e["type"] for e in seen} <= FAMILY_TYPES
    assert [e["kind"] for e in seen if e["type"] == "alert"] == ["codeword", "hangup"]
    assert [e["kind"] for e in seen if e["type"] == "intervention"] == ["codeword", "hangup"]
    assert seen[-1]["type"] == "call_ended"


def test_family_and_elder_see_the_same_family_events_in_the_same_order(client, new_call):
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder, \
         client.websocket_connect(call.events_url("family")) as family:
        seen_elder, seen_family = play_full_scam(client, call, elder, family)
    assert [e for e in seen_elder if e["type"] in FAMILY_TYPES] == seen_family


def test_family_connecting_after_the_alert_gets_it_first(client, new_call):
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder, \
         client.websocket_connect(call.captions_url) as cap:
        send_call(cap, call, SCAM_UNTIL_CODEWORD)
        before = recv_until(elder, is_type("alert", kind="codeword"))
        expected = [e for e in before if e["type"] in FAMILY_TYPES]

        with client.websocket_connect(call.events_url("family")) as family:
            replayed = [recv(family) for _ in expected]
            assert replayed == expected  # in order, alert included, nothing else first
            assert replayed[-1]["alert_id"] == f"{call.id}:codeword"
            assert drain(family) == []  # each past event once, no duplicates


def test_family_reconnect_replays_again(client, new_call):
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder, \
         client.websocket_connect(call.captions_url) as cap:
        send_call(cap, call, SCAM_UNTIL_CODEWORD)
        before = recv_until(elder, is_type("alert", kind="codeword"))
        expected = [e for e in before if e["type"] in FAMILY_TYPES]
        for _ in range(2):  # phone drops off the Wi-Fi and comes back
            with client.websocket_connect(call.events_url("family")) as family:
                assert [recv(family) for _ in expected] == expected


def test_elder_reconnect_replays_captions_and_events_in_order(client, new_call):
    call = new_call()
    with client.websocket_connect(call.captions_url) as cap:
        with client.websocket_connect(call.events_url("elder")) as elder:
            send_call(cap, call, SCAM_UNTIL_CODEWORD)
            before = recv_until(elder, is_type("alert", kind="codeword"))
        with client.websocket_connect(call.events_url("elder")) as elder2:
            assert [recv(elder2) for _ in before] == before


def test_listener_joining_mid_call_then_gets_live_events(client, new_call):
    call = new_call()
    with client.websocket_connect(call.captions_url) as cap:
        send_call(cap, call, SCAM_UNTIL_CODEWORD)
        with client.websocket_connect(call.events_url("family")) as family:
            recv_until(family, is_type("alert", kind="codeword"))  # replayed
            send_call(cap, call, [c for c in SCAM if c not in SCAM_UNTIL_CODEWORD], elder=None)
            recv_until(family, is_type("alert", kind="hangup"))  # live
