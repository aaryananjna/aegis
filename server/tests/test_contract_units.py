"""Unit checks for the two pure helpers the endpoints use: messages.parse and roles.allowed."""
import pytest

from aegis_server import messages, roles
from aegis_server.messages import CAPTIONS_INBOUND, ELDER_INBOUND
from helpers import FAMILY_TYPES, SCAM

pytestmark = pytest.mark.xfail(strict=False, reason="not implemented yet")


# ---- messages.parse ------------------------------------------------------------------------
@pytest.mark.parametrize("ok", [True, False])
def test_parse_codeword_result_keeps_a_real_bool(ok):
    assert messages.parse({"type": "codeword_result", "ok": ok}, ELDER_INBOUND) == \
        ("codeword_result", ok)


@pytest.mark.parametrize("ok", ["false", "true", 0, 1, None, 0.0, [], {}])
def test_parse_codeword_result_rejects_anything_else(ok):
    assert messages.parse({"type": "codeword_result", "ok": ok}, ELDER_INBOUND) is None


def test_parse_codeword_result_without_ok_is_rejected():
    assert messages.parse({"type": "codeword_result"}, ELDER_INBOUND) is None


@pytest.mark.parametrize("speaker", ["0", "1", None])
def test_parse_set_elder(speaker):
    assert messages.parse({"type": "set_elder", "speaker_raw": speaker}, ELDER_INBOUND) == \
        ("set_elder", speaker)


def test_parse_caption_and_end():
    kind, payload = messages.parse(SCAM[1], CAPTIONS_INBOUND)
    assert kind == "caption" and payload is not None
    assert messages.parse({"type": "end"}, CAPTIONS_INBOUND)[0] == "end"


@pytest.mark.parametrize("msg, allowed", [
    ({"type": "codeword_result", "ok": False}, CAPTIONS_INBOUND),  # wrong socket
    ({"type": "end"}, ELDER_INBOUND),                               # wrong socket
    ({"type": "caption", **SCAM[1]}, ELDER_INBOUND),                 # wrong socket
    ({"type": "end"}, set()),                                        # role=family
    ({"type": "no_such_type"}, CAPTIONS_INBOUND),
    ({"text": "no type"}, CAPTIONS_INBOUND),
    (["not", "a", "dict"], CAPTIONS_INBOUND),
    ("a string", CAPTIONS_INBOUND),
    (None, CAPTIONS_INBOUND),
    ({"type": "caption", "text": "missing fields"}, CAPTIONS_INBOUND),
    ({**SCAM[1], "revision": "two"}, CAPTIONS_INBOUND),
])
def test_parse_drops_bad_or_misplaced_messages(msg, allowed):
    assert messages.parse(msg, allowed) is None


# ---- roles.allowed -------------------------------------------------------------------------
ALL_TYPES = ["caption", "tactic_set", "risk", "intervention", "alert", "codeword_ok",
             "status", "call_ended"]


@pytest.mark.parametrize("event_type", ALL_TYPES)
def test_elder_gets_everything(event_type):
    assert roles.allowed("elder", {"type": event_type}) is True


@pytest.mark.parametrize("event_type", ALL_TYPES)
def test_family_gets_only_its_five_types(event_type):
    assert roles.allowed("family", {"type": event_type}) is (event_type in FAMILY_TYPES)


def test_unknown_role_gets_nothing():
    assert roles.allowed("admin", {"type": "alert"}) is False
