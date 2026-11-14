"""Sessions, tokens and the end of a call (CONTRACTS v2.1: Transport C3, End of call C5)."""
import pytest
from starlette.websockets import WebSocketDisconnect

from helpers import SCAM, is_type, recv_until, send_call, token_of

pytestmark = pytest.mark.xfail(strict=False, reason="not implemented yet")

BAD_TOKEN = 4401


def closed_with(client, url: str) -> int | None:
    """The close code if the server refuses this socket, else None."""
    try:
        with client.websocket_connect(url) as ws:
            ws.close()
    except WebSocketDisconnect as exc:
        return exc.code
    return None


def test_post_sessions_returns_id_and_both_links(client):
    r = client.post("/sessions")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["session_id"], str) and body["session_id"]
    for key in ("elder_url", "family_url"):
        assert body["session_id"] in body[key]
        assert token_of(body[key])


def test_tokens_differ_per_role_and_per_session(new_call):
    a, b = new_call(), new_call()
    assert a.id != b.id
    tokens = [a.elder_token, a.family_token, b.elder_token, b.family_token]
    assert len(set(tokens)) == 4


def test_each_token_opens_its_own_role(client, new_call):
    call = new_call()
    assert closed_with(client, call.events_url("elder")) is None
    assert closed_with(client, call.events_url("family")) is None


@pytest.mark.parametrize("case", ["wrong token", "family token as elder",
                                  "elder token as family", "other session's token"])
def test_events_refuses_a_bad_token_with_4401(client, new_call, case):
    call, other = new_call(), new_call()
    url = {
        "wrong token": call.events_url("elder", "not-a-real-token"),
        "family token as elder": call.events_url("elder", call.family_token),
        "elder token as family": call.events_url("family", call.elder_token),
        "other session's token": call.events_url("elder", other.elder_token),
    }[case]
    assert closed_with(client, url) == BAD_TOKEN


def test_end_on_captions_sends_call_ended_to_every_listener(client, new_call):
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder, \
         client.websocket_connect(call.events_url("family")) as family, \
         client.websocket_connect(call.captions_url) as cap:
        send_call(cap, call, SCAM[:3])
        cap.send_json({"type": "end", "session_id": call.id})
        for ws in (elder, family):
            ended = recv_until(ws, is_type("call_ended"))[-1]
            assert ended["session_id"] == call.id
            assert isinstance(ended["t"], (int, float))
            assert "seq" not in ended  # server events carry no seq (Envelope)


def test_tokens_stop_working_after_the_call_ends(client, new_call):
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder, \
         client.websocket_connect(call.captions_url) as cap:
        cap.send_json({"type": "end"})
        recv_until(elder, is_type("call_ended"))
    assert closed_with(client, call.events_url("elder")) == BAD_TOKEN
    assert closed_with(client, call.events_url("family")) == BAD_TOKEN


def test_http_end_does_the_same_as_an_end_message(client, new_call):
    call = new_call()
    with client.websocket_connect(call.events_url("family")) as family:
        assert client.post(f"/sessions/{call.id}/end").status_code == 200
        recv_until(family, is_type("call_ended"))
    assert closed_with(client, call.events_url("family")) == BAD_TOKEN


def test_end_reaches_the_detector_once(client, new_call, detector_spy):
    call = new_call()
    with client.websocket_connect(call.events_url("elder")) as elder, \
         client.websocket_connect(call.captions_url) as cap:
        cap.send_json({"type": "end"})
        recv_until(elder, is_type("call_ended"))
    assert len(detector_spy.names("end")) == 1
