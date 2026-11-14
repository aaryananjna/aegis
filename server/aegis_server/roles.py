"""Which events each listener role receives (CONTRACTS v2.1, C1 and C4)."""
from __future__ import annotations

ROLES = {"elder", "family"}

# Family phones never get captions, highlights or the risk meter.
# TODO: add the "code word answered right" event once B names it (issue #10).
FAMILY_EVENTS = {"alert", "intervention", "status", "call_ended"}


def allowed(role: str, event: dict) -> bool:
    """True if a listener with this role should receive this event."""
    raise NotImplementedError
