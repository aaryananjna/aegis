"""Fixtures for the contract tests. Plain helpers live in helpers.py."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aegis_server.main import app
from helpers import HOTSPOT_PHONE, LOCALHOST, Call, DetectorSpy


# ---- clients -------------------------------------------------------------------------------
@pytest.fixture
def client():
    """A client on the laptop itself (allowed to open /captions, C14)."""
    with TestClient(app, client=LOCALHOST) as c:
        yield c


@pytest.fixture
def remote_client():
    """A client from another device on the hotspot (must be refused on /captions, C14)."""
    with TestClient(app, client=HOTSPOT_PHONE) as c:
        yield c


# ---- sessions --------------------------------------------------------------------------------
@pytest.fixture
def new_call(client):
    def make() -> Call:
        r = client.post("/sessions")
        assert r.status_code == 200, r.text
        return Call(r.json())
    return make


# ---- watching the detector -----------------------------------------------------------------
@pytest.fixture
def detector_spy(monkeypatch):
    from hangup_detect.pipeline import Detector

    spy = DetectorSpy()
    for name in ("feed", "tick", "set_elder", "codeword_result", "end"):
        real = getattr(Detector, name)

        def wrapper(self, *args, _real=real, _name=name, **kwargs):
            spy.calls.append((_name, args))
            return _real(self, *args, **kwargs)

        monkeypatch.setattr(Detector, name, wrapper)
    return spy
