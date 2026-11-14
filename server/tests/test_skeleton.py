"""The skeleton starts and every endpoint from CONTRACTS v2.1 exists."""
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from aegis_server.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json()["ok"] is True


def test_http_routes_exist():
    paths = set(app.openapi()["paths"])
    for p in ("/health", "/sessions", "/sessions/{session_id}/end",
              "/auth/signup", "/auth/login", "/auth/logout"):
        assert p in paths


def test_laptop_only_endpoints_refuse_the_tunnel():
    fwd = {"X-Forwarded-For": "1.2.3.4"}
    assert client.post("/sessions", headers=fwd).status_code == 403
    assert client.post("/sessions/s1/end", headers=fwd).status_code == 403


@pytest.mark.parametrize("url, code", [
    ("/captions/s1", 1008),
    ("/events/s1?role=elder&token=x", 4401),
])
def test_websockets_exist_and_close(url, code):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(url) as ws:
            ws.receive_text()
    assert exc.value.code == code
