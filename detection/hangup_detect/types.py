"""Core data types. Shapes are frozen by the plan (Interfaces section)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

MAX_TEXT = 2000
SPEAKERS = {"caller", "elder", "unknown"}


class Tactic(str, Enum):
    IMPERSONATION = "impersonation"
    URGENCY = "urgency"
    SECRECY = "secrecy"
    PAYMENT = "payment"
    THREAT = "threat"
    VERIFICATION_AVOIDANCE = "verification_avoidance"
    REMOTE_ACCESS = "remote_access"
    DISTRESS = "distress"


@dataclass(frozen=True)
class Segment:
    utterance_id: str
    revision: int
    speaker: str
    text: str
    start_s: float
    end_s: float
    is_final: bool
    speaker_raw: str | None = None
    truncated: bool = False


@dataclass(frozen=True)
class Evidence:
    tactic: Tactic
    quote: str
    utterance_id: str
    span: tuple[int, int]
    source: str  # "rule" | "llm"
    t_s: float

    def as_dict(self) -> dict:
        return {"tactic": self.tactic.value, "quote": self.quote,
                "span": list(self.span), "source": self.source}


def make_segment(utterance_id: str, revision: int, speaker: str, text: str,
                 start_s: float, end_s: float, is_final: bool,
                 speaker_raw: str | None = None) -> Segment:
    """Build a Segment from untrusted input: clean speaker, cap text, check times."""
    for name, v in (("start_s", start_s), ("end_s", end_s)):
        if not math.isfinite(v) or v < 0:
            raise ValueError(f"{name} must be finite and >= 0, got {v}")
    if end_s < start_s:
        raise ValueError(f"end_s {end_s} is before start_s {start_s}")
    text = text or ""
    truncated = len(text) > MAX_TEXT
    return Segment(
        utterance_id=str(utterance_id), revision=int(revision),
        speaker=speaker if speaker in SPEAKERS else "unknown",
        text=text[:MAX_TEXT], start_s=float(start_s), end_s=float(end_s),
        is_final=bool(is_final), truncated=truncated,
        speaker_raw=None if speaker_raw is None else str(speaker_raw),
    )
