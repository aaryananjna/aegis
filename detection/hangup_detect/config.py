"""Every tunable number from the plan's Model section, in one place."""
from __future__ import annotations

from dataclasses import dataclass, field

from .types import Tactic

T = Tactic


def _weights() -> dict[Tactic, float]:
    return {T.IMPERSONATION: 1.2, T.URGENCY: 0.8, T.SECRECY: 1.5, T.PAYMENT: 2.0,
            T.THREAT: 1.5, T.VERIFICATION_AVOIDANCE: 2.0, T.REMOTE_ACCESS: 2.0,
            T.DISTRESS: 0.6}


def _combos() -> dict[tuple[Tactic, Tactic], float]:
    return {(T.IMPERSONATION, T.PAYMENT): 1.5, (T.IMPERSONATION, T.SECRECY): 1.0,
            (T.SECRECY, T.PAYMENT): 1.0, (T.URGENCY, T.PAYMENT): 0.8,
            (T.THREAT, T.PAYMENT): 1.0, (T.REMOTE_ACCESS, T.IMPERSONATION): 1.5}


@dataclass
class Config:
    weights: dict[Tactic, float] = field(default_factory=_weights)
    combos: dict[tuple[Tactic, Tactic], float] = field(default_factory=_combos)
    prior: float = -3.0
    llm_mixed: bool = True  # labels off: let the AI read both voices once the rules have fired
    llm_fail_streak: int = 3  # AI failures in a row before the screens say rules only
    llm_min_interval_s: float = 8.0  # at most one AI request per 8 s (free-tier token limits)
    llm_mixed_always: bool = True  # labels off: let the AI read both voices from the first line
    half_life_s: float = 120.0
    horizon_s: float = 600.0
    second_hit_factor: float = 0.5
    llm_factor: float = 0.7
    llm_cap: float = 1.5
    # AI alarm: when the AI quotes at least this many different tactics, it may raise the
    # level on its own (no rule needed) and its cap rises to ai_alarm_cap. 0 = off.
    ai_alarm_tactics: int = 2
    ai_alarm_cap: float = 3.0
    combo_cap: float = 2.0
    enter_high: float = 0.80
    exit_high: float = 0.60
    enter_elevated: float = 0.50
    exit_elevated: float = 0.35
    hangup_score: float = 0.95
    codeword_min_s: float = 20.0
    risk_emit_delta: float = 0.01
    max_finals: int = 2000

    def validate(self) -> "Config":
        if any(w < 0 for w in self.weights.values()) or set(self.weights) != set(Tactic):
            raise ValueError("weights must cover all 8 tactics and be >= 0")
        if any(b < 0 for b in self.combos.values()):
            raise ValueError("combos must be >= 0")
        for name in ("half_life_s", "horizon_s"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be > 0")
        for name in ("llm_cap", "combo_cap"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be >= 0")
        for name in ("enter_high", "exit_high", "enter_elevated", "exit_elevated", "hangup_score"):
            if not 0 < getattr(self, name) < 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if not self.exit_high < self.enter_high:
            raise ValueError("exit_high must be below enter_high")
        if not self.exit_elevated < self.enter_elevated:
            raise ValueError("exit_elevated must be below enter_elevated")
        return self
