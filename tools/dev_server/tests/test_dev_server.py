"""The v2.1 behaviors C's screens rely on. Run: cd tools/dev_server && pytest -q"""
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import aegis_dev_server as dev

dev.LOCAL_HOSTS.add("testclient")  # TestClient's fake client address counts as the laptop

SCAM = [("0", "Hello?"),
        ("1", "Nana, it's me. Please don't tell Mom."),
        ("1", "I need bail money right now. They only take gift cards.")]


@pytest.fixture
def client():
    with TestClient(dev.app) as c:
        yield c


def new_session(client):
    r = client.post("/sessions", json={"name": "Rose", "phone": "+15550100"})
    assert r.status_code == 200
    body = r.json()
    q = {role: parse_qs(urlparse(body[f"{role}_url"]).query) for role in ("elder", "family")}
    return body["session_id"], q["elder"]["token"][0], q["family"]["token"][0], q


def caption(uid, spk, text):
    return {"type": "caption", "utterance_id": uid, "revision": 0, "speaker_raw": spk,
            "text": text, "start_s": 0, "end_s": 1, "is_final": True}


def until(ws, etype, **match):
    """Read events until one of type `etype` (matching fields) arrives; return everything read."""
    seen = []
    while True:
        e = ws.receive_json()
        seen.append(e)
        if e["type"] == etype and all(e.get(k) == v for k, v in match.items()):
            return seen


def test_session_links_carry_tokens_and_display_fields(client):
    sid, elder, family, q = new_session(client)
    assert elder != family
    assert q["family"]["name"] == ["Rose"] and q["family"]["phone"] == ["+15550100"]
    assert "name" not in q["elder"]
    assert client.get("/health").json()["ok"] is True


@pytest.mark.parametrize("role,which", [("elder", "family"), ("family", "elder"), ("elder", "bad")])
def test_wrong_or_other_role_token_closes_4401(client, role, which):
    sid, elder, family, _ = new_session(client)
    token = {"elder": elder, "family": family, "bad": "nope"}[which]
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/events/{sid}?role={role}&token={token}") as ws:
            ws.receive_json()
    assert exc.value.code == dev.BAD_TOKEN


def test_full_call_elder_gets_captions_first_family_gets_only_its_events(client):
    sid, elder, family, _ = new_session(client)
    with client.websocket_connect(f"/events/{sid}?role=elder&token={elder}") as ew, \
         client.websocket_connect(f"/events/{sid}?role=family&token={family}") as fw, \
         client.websocket_connect(f"/captions/{sid}") as cw:
        ew.send_json({"type": "set_elder", "speaker_raw": "0"})  # C3: tap arrives on /events
        for i, (spk, text) in enumerate(SCAM):
            cw.send_json(caption(f"u{i}", spk, text))
        seen = until(ew, "intervention", kind="codeword")
        caps = [e for e in seen if e["type"] == "caption"]
        assert [c["text"] for c in caps] == [t for _, t in SCAM]  # C1
        first_hl = next(i for i, e in enumerate(seen) if e["type"] == "tactic_set")
        cap_u1 = next(i for i, e in enumerate(seen) if e["type"] == "caption" and e["utterance_id"] == "u1")
        assert cap_u1 < first_hl  # caption before its highlights
        fam = until(fw, "alert", kind="codeword")
        assert {e["type"] for e in fam} <= dev.FAMILY_EVENTS  # C4

        ew.send_json({"type": "codeword_result", "ok": False})  # C12 over /events
        until(ew, "intervention", kind="hangup")


def test_codeword_ok_reaches_family(client):
    sid, elder, family, _ = new_session(client)
    with client.websocket_connect(f"/events/{sid}?role=elder&token={elder}") as ew, \
         client.websocket_connect(f"/events/{sid}?role=family&token={family}") as fw, \
         client.websocket_connect(f"/captions/{sid}") as cw:
        ew.send_json({"type": "set_elder", "speaker_raw": "0"})
        for i, (spk, text) in enumerate(SCAM):
            cw.send_json(caption(f"u{i}", spk, text))
        until(ew, "intervention", kind="codeword")
        ew.send_json({"type": "codeword_result", "ok": "false"})  # not a bool: ignored
        ew.send_json({"type": "codeword_result", "ok": True})
        until(fw, "codeword_ok")


def test_reconnect_replays_past_events(client):
    sid, elder, family, _ = new_session(client)
    with client.websocket_connect(f"/events/{sid}?role=elder&token={elder}") as ew, \
         client.websocket_connect(f"/captions/{sid}") as cw:
        ew.send_json({"type": "set_elder", "speaker_raw": "0"})
        for i, (spk, text) in enumerate(SCAM):
            cw.send_json(caption(f"u{i}", spk, text))
        until(ew, "alert", kind="codeword")
    with client.websocket_connect(f"/events/{sid}?role=family&token={family}") as fw:
        replayed = until(fw, "alert", kind="codeword")  # C6: a late family page still sees it
        assert all(e["type"] in dev.FAMILY_EVENTS for e in replayed)


def test_typed_line_becomes_typed_caption(client):
    sid, elder, _, _ = new_session(client)
    with client.websocket_connect(f"/events/{sid}?role=elder&token={elder}") as ew:
        r = client.post("/typed", json={"session_id": sid, "text": "Grandma, it's me",
                                        "speaker_raw": "1"})
        assert r.status_code == 200
        cap = until(ew, "caption")[-1]
        assert cap["source"] == "typed" and cap["is_final"] and cap["text"] == "Grandma, it's me"
    assert client.post("/typed", json={"session_id": "nope", "text": "x"}).status_code == 404
    assert client.post("/typed", json={"session_id": sid, "text": "  "}).status_code == 422


def test_end_sends_call_ended_then_tokens_stop_working(client):
    sid, elder, family, _ = new_session(client)
    with client.websocket_connect(f"/events/{sid}?role=family&token={family}") as fw:
        assert client.post(f"/sessions/{sid}/end").status_code == 200
        until(fw, "call_ended")  # C5
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/events/{sid}?role=family&token={family}") as fw:
            fw.receive_json()
    assert exc.value.code == dev.BAD_TOKEN


def test_captions_socket_and_http_refuse_other_machines(client, monkeypatch):
    monkeypatch.setattr(dev, "LOCAL_HOSTS", {"127.0.0.1"})
    assert client.post("/sessions").status_code == 403
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/captions/x") as cw:
            cw.receive_json()
    assert exc.value.code == dev.POLICY_VIOLATION
