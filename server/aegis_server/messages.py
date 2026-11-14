"""Checks every inbound message before it reaches a session's queue.

Bad input is dropped here (and logged without text), so one malformed message can't stop
detection. Inbound types per CONTRACTS v2.1:
  /captions: caption, set_elder, end
  /events (role=elder): set_elder, codeword_result, end (the screen's "End call" button)
  /events (role=family): nothing (ignored)
"""
from __future__ import annotations

import json
import logging
from typing import Any

from hangup_detect import make_segment

log = logging.getLogger("aegis.messages")

CAPTIONS_INBOUND = frozenset({"caption", "set_elder", "end"})
ELDER_INBOUND = frozenset({"set_elder", "codeword_result", "end"})  # end: "End call" button

MAX_MESSAGE_BYTES = 16_384   # one caption is far smaller; anything bigger is refused
MAX_ID_LEN = 64

QueueItem = tuple[str, Any]


def _speaker(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (str, int)):
        raise TypeError("speaker_raw must be a string, a number or null")
    v = str(v)
    if not v or len(v) > MAX_ID_LEN:
        raise ValueError("speaker_raw has a bad length")
    return v


def decode(raw: str | bytes) -> Any:
    """JSON text -> object, or None if it's too big or not JSON."""
    if len(raw) > MAX_MESSAGE_BYTES:
        return None
    try:
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return None


def parse(msg: Any, allowed_types: frozenset[str] | set[str]) -> QueueItem | None:
    """Turn one JSON message into a (kind, payload) queue item, or None if it's bad.

    codeword_result: `ok` must be a real bool, never coerced (issue #10).
    """
    kind = msg.get("type") if isinstance(msg, dict) else None
    if kind not in allowed_types:
        log.warning("ignored message type %r", kind if isinstance(kind, str) else type(kind))
        return None
    try:
        if kind == "caption":
            uid = msg["utterance_id"]
            if not isinstance(uid, str) or not 0 < len(uid) <= MAX_ID_LEN:
                raise ValueError("bad utterance_id")
            rev = msg["revision"]
            if isinstance(rev, bool) or not isinstance(rev, int) or rev < 0:
                raise ValueError("bad revision")
            text = msg["text"]
            if not isinstance(text, str):
                raise TypeError("text must be a string")
            is_final = msg["is_final"]
            if not isinstance(is_final, bool):
                raise TypeError("is_final must be true or false")
            start, end = msg["start_s"], msg["end_s"]
            if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in (start, end)):
                raise TypeError("times must be numbers")
            source = msg.get("source", "live")
            seg = make_segment(uid, rev, "unknown", text, start, end, is_final,
                               speaker_raw=_speaker(msg.get("speaker_raw")))
            return kind, (seg, source if source in ("live", "typed") else "live")
        if kind == "set_elder":
            return kind, _speaker(msg.get("speaker_raw"))
        if kind == "codeword_result":
            if not isinstance(msg["ok"], bool):  # never coerce "false" (issue #10)
                raise TypeError("ok must be true or false")
            return kind, msg["ok"]
        return kind, None  # end
    except (KeyError, TypeError, ValueError) as exc:
        log.warning("bad %s message skipped: %s", kind, type(exc).__name__)
        return None
