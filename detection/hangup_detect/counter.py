"""Counter-moves: one calm card at a time for the elder, one alert per card.

Cards are latched safety advice: none -> codeword -> hangup, never backwards
within a call, one step per update. A dodge after the codeword card escalates
at once; a very high score alone waits codeword_min_s so Grandma gets a real
chance to ask the code word first.
"""
from __future__ import annotations

from .config import Config
from .types import Tactic as T

CARD_TEXT = {
    "codeword": "This might not be who they say. Ask: what's our family code word?",
    "hangup": "Hang up. Call back on the saved number.",
}

PHRASES = {
    T.IMPERSONATION: "claimed to be someone you know or an official",
    T.URGENCY: "rushed the call",
    T.SECRECY: "asked for secrecy",
    T.PAYMENT: "asked for gift cards, crypto or a wire transfer",
    T.THREAT: "made threats",
    T.VERIFICATION_AVOIDANCE: "dodged questions",
    T.REMOTE_ACCESS: "asked to control the computer",
    T.DISTRESS: "sounded panicked",
}


def summary(tactics: set[T]) -> str:
    parts = [PHRASES[t] for t in T if t in tactics]
    if not parts:
        return "Caller showed signs of a scam."
    text = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    return f"Caller {text}."


class CounterMoves:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.state = "none"
        self._codeword_at: float | None = None

    def update(self, level: str, score: float, new_rule_tactics: set[T],
               live_tactics: set[T], ranked_quotes: list[str], now: float) -> list[tuple]:
        """Return actions: ("intervention", kind, text) and ("alert", kind, quotes, summary)."""
        nxt = None
        if self.state == "none" and level == "high":
            nxt = "codeword"
        elif self.state == "codeword" and (
                T.VERIFICATION_AVOIDANCE in new_rule_tactics
                or (score >= self.cfg.hangup_score
                    and now - self._codeword_at >= self.cfg.codeword_min_s)):
            nxt = "hangup"
        if nxt is None:
            return []
        self.state = nxt
        if nxt == "codeword":
            self._codeword_at = now
        return [("intervention", nxt, CARD_TEXT[nxt]),
                ("alert", nxt, ranked_quotes[:3], summary(live_tactics))]
