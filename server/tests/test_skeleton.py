"""The skeleton starts and every endpoint from CONTRACTS v2.1 exists."""
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from aegis_server.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"ok": True}


def test_http_routes_exist():
    paths = set(app.openapi()["paths"])
    for p in ("/health", "/sessions", "/sessions/{session_id}/end",
              "/auth/signup", "/auth/login", "/auth/logout"):
        assert p in paths


def test_unbuilt_http_endpoints_say_so():
    assert client.post("/sessions").status_code == 501
    assert client.post("/sessions/s1/end").status_code == 501


@pytest.mark.parametrize("url, code", [
    ("/captions/s1", 1008),
    ("/events/s1?role=elder&token=x", 4401),
])
def test_websockets_exist_and_close(url, code):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(url) as ws:
            ws.receive_text()
    assert exc.value.code == code
