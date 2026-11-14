"""What each socket accepts from clients (CONTRACTS v2.1: C3, C12, C14, messages.py)."""
import logging
import time

import pytest
from starlette.websockets import WebSocketDisconnect

from helpers import (SCAM, SCAM_AFTER_CODEWORD, SCAM_UNTIL_CODEWORD, drain, is_type, recv,
                     recv_until, send_call)

pytestmark = pytest.mark.xfail(strict=False, reason="not implemented yet")

POLICY_VIOLATION = 1008


def up_to_codeword_card(client, call, cap, elder):
    send_call(cap, call, SCAM_UNTIL_CODEWORD)
    recv_until(elder, is_type("alert", kind="codeword"))


# ---- /captions is laptop only (C14) --------------------------------------------------------
def test_captions_refuses_other_devices_with_1008(new_call, remote_client):
    call = new_call()  # a real session, so the refusal is about the client, not the id
    with pytest.raises(WebSocketDisconnect) as exc:
        with remote_client.websocket_connect(call.captions_url) as ws:
            ws.send_json({**SCAM[0], "session_id": call.id})
            recv(ws)
    assert exc.value.code == POLICY_VIOLATION


def test_captions_accepts_the_laptop(client, new_call):
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder, \
         client.websocket_connect(call.captions_url) as cap:
        send_call(cap, call, SCAM[:1], elder=None)
        assert recv_until(elder, is_type("caption"))[-1]["utterance_id"] == SCAM[0]["utterance_id"]


# ---- codeword_result (C12) -----------------------------------------------------------------
@pytest.mark.parametrize("bad_ok", ["false", 0, None, "true", 1, [], {}],
                         ids=["str-false", "zero", "null", "str-true", "one", "list", "dict"])
def test_codeword_result_with_non_bool_ok_never_reaches_detector(client, new_call,
                                                                detector_spy, bad_ok):
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder, \
         client.websocket_connect(call.captions_url) as cap:
        up_to_codeword_card(client, call, cap, elder)
        elder.send_json({"type": "codeword_result", "session_id": call.id, "ok": bad_ok})
        # A real answer on the same socket afterwards. If the bad one had got through it would
        # have been "the first one", so this would be ignored (or the hangup card shown).
        elder.send_json({"type": "codeword_result", "ok": True})
        seen = recv_until(elder, is_type("codeword_ok"))
    oks = [a[0] for a in detector_spy.names("codeword_result")]
    assert oks == [True] and all(type(ok) is bool for ok in oks)
    assert not [e for e in seen if e["type"] == "intervention" and e["kind"] == "hangup"]


def test_codeword_result_missing_ok_is_dropped(client, new_call, detector_spy):
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder, \
         client.websocket_connect(call.captions_url) as cap:
        up_to_codeword_card(client, call, cap, elder)
        elder.send_json({"type": "codeword_result"})
        elder.send_json({"type": "codeword_result", "ok": True})
        recv_until(elder, is_type("codeword_ok"))
    assert [a[0] for a in detector_spy.names("codeword_result")] == [True]


def test_wrong_codeword_gives_the_hangup_card_at_once(client, new_call):
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder, \
         client.websocket_connect(call.events_url("family")) as family, \
         client.websocket_connect(call.captions_url) as cap:
        up_to_codeword_card(client, call, cap, elder)
        elder.send_json({"type": "codeword_result", "session_id": call.id, "ok": False})
        # No more captions: the card must come from the answer alone.
        seen = recv_until(elder, is_type("alert", kind="hangup"))
        assert [e["kind"] for e in seen if e["type"] == "intervention"] == ["hangup"]
        recv_until(family, is_type("alert", kind="hangup"))


def test_right_codeword_sends_codeword_ok_to_family_too(client, new_call):
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder, \
         client.websocket_connect(call.events_url("family")) as family, \
         client.websocket_connect(call.captions_url) as cap:
        up_to_codeword_card(client, call, cap, elder)
        elder.send_json({"type": "codeword_result", "ok": True})
        ok = recv_until(elder, is_type("codeword_ok"))[-1]
        assert ok["resolves"] == f"{call.id}:codeword"
        assert recv_until(family, is_type("codeword_ok"))[-1] == ok


def test_set_elder_on_the_elder_socket_reaches_the_detector(client, new_call, detector_spy):
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder, \
         client.websocket_connect(call.captions_url) as cap:
        send_call(cap, call, SCAM_UNTIL_CODEWORD, elder=None)
        recv_until(elder, is_type("caption", utterance_id=SCAM_UNTIL_CODEWORD[-1]["utterance_id"]))
        elder.send_json({"type": "set_elder", "session_id": call.id, "speaker_raw": "0"})
        recv_until(elder, is_type("alert", kind="codeword"))  # cards wait for set_elder
    assert [a[0] for a in detector_spy.names("set_elder")] == ["0"]


# ---- role=family is read only (C3, C4) -----------------------------------------------------
def test_family_inbound_is_ignored(client, new_call, detector_spy):
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder, \
         client.websocket_connect(call.events_url("family")) as family, \
         client.websocket_connect(call.captions_url) as cap:
        up_to_codeword_card(client, call, cap, elder)
        set_elder_before = len(detector_spy.names("set_elder"))
        for msg in ({"type": "codeword_result", "ok": False},
                    {"type": "set_elder", "speaker_raw": "1"},
                    {"type": "end"},
                    {**SCAM_AFTER_CODEWORD[-1], "session_id": call.id}):
            family.send_json(msg)
        family.send_text("not json")
        time.sleep(0.3)

        assert detector_spy.names("codeword_result") == []
        assert len(detector_spy.names("set_elder")) == set_elder_before
        assert detector_spy.names("end") == []
        late = drain(elder)
        assert not [e for e in late if e["type"] in ("caption", "call_ended")]
        assert not [e for e in late if e.get("kind") == "hangup"]

        # The family socket is still open and the call still running.
        cap.send_json({"type": "end"})
        recv_until(family, is_type("call_ended"))


# ---- bad input can't stop detection (messages.py) ------------------------------------------
def test_malformed_messages_are_dropped_and_the_session_keeps_going(client, new_call):
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder, \
         client.websocket_connect(call.captions_url) as cap:
        cap.send_text("not json at all")
        cap.send_json(["a", "list"])
        cap.send_json({"type": "caption", "text": "missing every other field"})
        cap.send_json({"type": "codeword_result", "ok": False})  # not accepted on /captions
        cap.send_json({"type": "no_such_type"})
        elder.send_json({"type": "end"})  # not accepted on /events
        elder.send_text("{broken")
        send_call(cap, call, SCAM[:2], elder=None)
        seen = recv_until(elder, is_type("caption", utterance_id=SCAM[1]["utterance_id"]))
    assert [e["utterance_id"] for e in seen if e["type"] == "caption"] == ["u0", "u1"]
    assert not [e for e in seen if e["type"] == "call_ended"]


def test_caption_text_is_not_logged(client, new_call, caplog):
    caplog.set_level(logging.DEBUG)
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder, \
         client.websocket_connect(call.captions_url) as cap:
        send_call(cap, call, SCAM)
        cap.send_json({"type": "caption", "utterance_id": "bad", "text": "secret words here"})
        cap.send_json({"type": "end"})
        recv_until(elder, is_type("call_ended"))
    for c in SCAM + [{"text": "secret words here"}]:
        assert c["text"] not in caplog.text
