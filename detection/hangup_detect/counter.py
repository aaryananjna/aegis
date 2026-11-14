"""Counter-moves: one calm card at a time for the elder, one alert per card.

Cards are latched safety advice: none -> codeword|verify -> hangup, never backwards
within a call, one step per update. A dodge after the codeword card escalates
at once; a very high score alone waits codeword_min_s so Grandma gets a real
chance to ask the code word first.
"""
from __future__ import annotations

from .config import Config
from .types import Tactic as T

CARD_TEXT = {
    # Caller claims to be family: the family code word is the right check.
    "codeword": "This might not be who they say. Ask: what's our family code word?",
    "hangup_family": "Hang up. Call back on the saved number.",
    # Caller claims to be a bank, the government or a company, or no one at all.
    "verify": "This might be a scam. Don't pay or share any numbers. Ask for their name and say you'll call back.",
    "hangup_other": "Hang up. Call the number on your card or their official website.",
}
FIRST_CARDS = {"codeword", "verify"}

PHRASES = {
    T.IMPERSONATION: "claimed to be someone you know or an official",
    T.URGENCY: "rushed the call",
    T.SECRECY: "asked for secrecy",
    T.PAYMENT: "asked to pay or move money in an unusual way",
    T.THREAT: "made threats",
    T.VERIFICATION_AVOIDANCE: "dodged questions",
    T.REMOTE_ACCESS: "asked to control the computer or for a code",
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
        self._family = True
        self._codeword_ok = False  # right code word given: score alone no longer escalates

    def codeword_result(self, ok: bool, ranked_quotes: list[str], live_tactics: set[T],
                        now: float) -> list[tuple]:
        """The elder screen reports the caller's answer to the code word card (C12).

        Wrong: hang up at once. Right: the score-based hang up path turns off, but a dodge
        still escalates. Ignored unless the code word card is showing.
        """
        if self.state != "codeword":
            return []
        if ok:
            self._codeword_ok = True
            return []
        return self._move("hangup", ranked_quotes, live_tactics, now)

    def update(self, level: str, score: float, new_rule_tactics: set[T],
               live_tactics: set[T], ranked_quotes: list[str], now: float,
               family: bool = True) -> list[tuple]:
        """Return actions: ("intervention", kind, text) and ("alert", kind, quotes, summary).

        family: the caller claimed to be family, so the first card asks for the code word.
        It's decided once, when the first card fires.
        """
        nxt = None
        if self.state == "none" and level == "high":
            nxt = "codeword" if family else "verify"
            self._family = family
        elif self.state in FIRST_CARDS and (
                T.VERIFICATION_AVOIDANCE in new_rule_tactics
                or (score >= self.cfg.hangup_score and not self._codeword_ok
                    and now - self._codeword_at >= self.cfg.codeword_min_s)):
            nxt = "hangup"
        if nxt is None:
            return []
        return self._move(nxt, ranked_quotes, live_tactics, now)

    def _move(self, nxt: str, ranked_quotes: list[str], live_tactics: set[T], now: float) -> list[tuple]:
        self.state = nxt
        if nxt in FIRST_CARDS:
            self._codeword_at = now
        text = CARD_TEXT[nxt] if nxt in FIRST_CARDS else CARD_TEXT[
            "hangup_family" if self._family else "hangup_other"]
        return [("intervention", nxt, text),
                ("alert", nxt, ranked_quotes[:3], summary(live_tactics))]
