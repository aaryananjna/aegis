"""Which events each listener role receives (CONTRACTS v2.1, C1 and C4)."""
from __future__ import annotations

ROLES = ("elder", "family")

# Family phones never get captions, highlights or the risk meter.
FAMILY_EVENTS = frozenset({"alert", "intervention", "codeword_ok", "status", "call_ended"})


def allowed(role: str, event: dict) -> bool:
    """True if a listener with this role should receive this event."""
    if role == "elder":
        return True
    return role == "family" and event.get("type") in FAMILY_EVENTS
