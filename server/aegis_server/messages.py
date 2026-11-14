"""Checks every inbound message before it reaches a session's queue.

Bad input is dropped here (and logged without text), so one malformed message can't stop
detection. Inbound types per CONTRACTS v2.1:
  /captions: caption, set_elder, end
  /events (role=elder): set_elder, codeword_result
  /events (role=family): nothing (ignored)
"""
from __future__ import annotations

from typing import Any

CAPTIONS_INBOUND = {"caption", "set_elder", "end"}
ELDER_INBOUND = {"set_elder", "codeword_result"}

QueueItem = tuple[str, Any]


def parse(msg: Any, allowed_types: set[str]) -> QueueItem | None:
    """Turn one JSON message into a (kind, payload) queue item, or None if it's bad.

    codeword_result: `ok` must be a real bool, never coerced (issue #10).
    """
    raise NotImplementedError
