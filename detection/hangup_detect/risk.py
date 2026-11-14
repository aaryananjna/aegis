"""Evidence-accumulation risk model. Math is the plan's Model section, line for line.

Rule evidence and LLM evidence live in separate ledgers. The LLM part per
tactic is max(0, llm - rule), so adding LLM evidence can never lower the
score (invariant 3).
"""
from __future__ import annotations

import math

from .config import Config
from .types import Evidence, Tactic

LOW, ELEVATED, HIGH = "low", "elevated", "high"


def next_level(prev: str, score: float, has_rule: bool, cfg: Config) -> str:
    """The plan's transition table. High always needs live rule evidence."""
    if score >= cfg.enter_high and has_rule:
        return HIGH
    if prev == HIGH:
        if score < cfg.exit_high or not has_rule:
            return ELEVATED if score >= cfg.exit_elevated else LOW
        return HIGH
    if prev == ELEVATED:
        return LOW if score < cfg.exit_elevated else ELEVATED
    return ELEVATED if score >= cfg.enter_elevated else LOW


class RiskModel:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.evidence: list[Evidence] = []
        self.level = LOW

    def add(self, e: Evidence) -> None:
        self.evidence.append(e)

    def clear(self) -> None:
        self.evidence.clear()
        self.level = LOW

    # ---- pure reads -------------------------------------------------
    def _live(self, now: float, source: str):
        return [e for e in self.evidence
                if e.source == source and 0 <= now - e.t_s < self.cfg.horizon_s]

    def _ledger(self, now: float, source: str) -> dict[Tactic, float]:
        factor = 1.0 if source == "rule" else self.cfg.llm_factor
        vals: dict[Tactic, list[float]] = {}
        for e in self._live(now, source):
            d = 0.5 ** ((now - e.t_s) / self.cfg.half_life_s)
            vals.setdefault(e.tactic, []).append(self.cfg.weights[e.tactic] * factor * d)
        out = {}
        for t, vs in vals.items():
            vs.sort(reverse=True)
            out[t] = vs[0] + (self.cfg.second_hit_factor * vs[1] if len(vs) > 1 else 0.0)
        return out

    def _parts(self, now: float, include_llm: bool):
        rule = self._ledger(now, "rule")
        llm: dict[Tactic, float] = {}
        if include_llm:
            raw = self._ledger(now, "llm")
            llm = {t: max(0.0, v - rule.get(t, 0.0)) for t, v in raw.items()}
            total = sum(llm.values())
            if total > self.cfg.llm_cap:
                k = self.cfg.llm_cap / total
                llm = {t: v * k for t, v in llm.items()}
        combined = {t: rule.get(t, 0.0) + llm.get(t, 0.0) for t in set(rule) | set(llm)}

        def strength(t):
            w = self.cfg.weights[t]
            return min(1.0, combined.get(t, 0.0) / w) if w > 0 else 0.0

        combos = {f"{a.value}+{b.value}": bonus * min(strength(a), strength(b))
                  for (a, b), bonus in self.cfg.combos.items()}
        combos = {k: v for k, v in combos.items() if v > 0}
        total = sum(combos.values())
        if total > self.cfg.combo_cap:
            k = self.cfg.combo_cap / total
            combos = {name: v * k for name, v in combos.items()}
        return rule, llm, combos

    def score(self, now: float, include_llm: bool = True) -> float:
        rule, llm, combos = self._parts(now, include_llm)
        x = self.cfg.prior + sum(rule.values()) + sum(llm.values()) + sum(combos.values())
        return 1 / (1 + math.exp(-x))

    def contributions(self, now: float) -> dict:
        rule, llm, combos = self._parts(now, True)
        r = lambda d: {k.value if isinstance(k, Tactic) else k: round(v, 6) for k, v in d.items()}
        return {"rule": r(rule), "llm": r(llm), "combos": r(combos)}

    def has_live_rule(self, now: float) -> bool:
        return bool(self._live(now, "rule"))

    # ---- the only mutator ---------------------------------------------
    def update_level(self, now: float) -> str:
        self.level = next_level(self.level, self.score(now), self.has_live_rule(now), self.cfg)
        return self.level
