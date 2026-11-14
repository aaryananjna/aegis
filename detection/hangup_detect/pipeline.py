"""Detector: the one object A's server talks to, one per call session.

Pure and synchronous. The caller passes the clock in, so live audio, typed
input and replayed files all run exactly the same code. Not thread safe:
one owner per session must serialize every call (see INTEGRATION.md).
"""
from __future__ import annotations

from collections import OrderedDict

from . import events as ev
from .config import Config
from .counter import CounterMoves
from .risk import RiskModel
from .rules import find_evidence
from .types import Evidence, Segment, Tactic


class Detector:
    def __init__(self, config: Config, session_id: str, elder_speaker_raw: str | None = None,
                 confirmed: bool = False):
        self.cfg = config.validate()
        self.session_id = session_id
        self.risk = RiskModel(self.cfg)
        self.counter = CounterMoves(self.cfg, session_id)
        self.elder_raw = elder_speaker_raw
        self.confirmed = confirmed or elder_speaker_raw is not None
        self.ended = False
        self._seq = 0
        self._now = 0.0
        self._last_rev: dict[str, int] = {}
        self._finals: OrderedDict[str, tuple[Segment, float]] = OrderedDict()
        self._llm_evidence: list[Evidence] = []
        self._shown: dict[str, list[dict]] = {}  # utterance_id -> evidence C currently shows
        self._last_score: float | None = None
        self._last_level = "low"
        self._timing: list[dict] = []

    # ---- public API -----------------------------------------------------
    def feed(self, seg: Segment, now_s: float) -> list[dict]:
        now = self._clock(now_s)
        uid = seg.utterance_id
        if uid in self._finals:
            if seg.is_final:
                return [self._status("duplicate final ignored")]
            return []  # interim after its final
        last = self._last_rev.get(uid)
        if last is not None and (seg.revision < last or (seg.revision == last and not seg.is_final)):
            return []  # stale revision (a final may reuse the last interim's revision)
        self._last_rev[uid] = seg.revision
        if not seg.is_final:
            return self._on_interim(seg, now)

        out: list[dict] = []
        self._finals[uid] = (seg, now)
        if len(self._finals) > self.cfg.max_finals:
            self._finals.popitem(last=False)
            out.append(self._status("oldest caption dropped from the rebuild store"))
        new_tactics: set[Tactic] = set()
        hits = []
        if self._role(seg) != "elder":
            hits = find_evidence(seg.text, uid, now)
            for h in hits:
                self.risk.add(h)
            new_tactics = {h.tactic for h in hits}
        out += self._set_highlights(uid, seg.revision, False, [h.as_dict() for h in hits], now)
        self._timing.append({"utterance_id": uid, "end_s": seg.end_s, "arrival_s": now,
                             "tactics": sorted(t.value for t in new_tactics)})
        out += self._evaluate(now, new_tactics)
        return out

    def tick(self, now_s: float) -> list[dict]:
        return self._evaluate(self._clock(now_s), set())

    def set_elder(self, speaker_raw: str | None, now_s: float) -> list[dict]:
        now = self._clock(now_s)
        self.elder_raw = speaker_raw
        self.confirmed = True
        self.risk.clear()
        out: list[dict] = []
        for uid, (seg, arrival) in self._finals.items():
            hits = [] if self._role(seg) == "elder" else find_evidence(seg.text, uid, arrival)
            for h in hits:
                self.risk.add(h)
            out += self._set_highlights(uid, seg.revision, False, [h.as_dict() for h in hits], now)
        for e in self._llm_evidence:
            if e.utterance_id in self._finals and self._role(self._finals[e.utterance_id][0]) != "elder":
                self.risk.add(e)
        self._last_score = None  # force a fresh risk event
        out += self._evaluate(now, set())
        return out

    def end(self, now_s: float) -> list[dict]:
        out = self.tick(now_s)
        self.ended = True
        return out

    def state(self) -> dict:
        now = self._now
        return {"session_id": self.session_id, "t": now, "score": self.risk.score(now),
                "level": self.risk.level, "intervention": self.counter.state,
                "confirmed": self.confirmed, "ended": self.ended,
                "timing": [dict(r) for r in self._timing]}

    # ---- internals ------------------------------------------------------
    def _on_interim(self, seg: Segment, now: float) -> list[dict]:
        return []  # S5b: provisional highlights

    def _clock(self, now_s: float) -> float:
        if self.ended:
            raise RuntimeError("detector has ended; start a new session")
        self._now = max(self._now, float(now_s))
        return self._now

    def _next(self) -> int:
        self._seq += 1
        return self._seq

    def _status(self, warning: str) -> dict:
        return ev.status(self.session_id, self._now, self._next(), "rules_only", warning)

    def _role(self, seg: Segment) -> str:
        if self.confirmed and self.elder_raw is not None and seg.speaker_raw is not None:
            return "elder" if seg.speaker_raw == self.elder_raw else "caller"
        return seg.speaker

    def _set_highlights(self, uid, revision, provisional, evidence, now) -> list[dict]:
        if not evidence and not self._shown.get(uid):
            return []
        self._shown[uid] = evidence
        return [ev.tactic_set(self.session_id, now, self._next(), uid, revision, provisional, evidence)]

    def _ranked(self, now: float) -> tuple[list[str], set[Tactic]]:
        live = [e for e in self.risk.evidence if 0 <= now - e.t_s < self.cfg.horizon_s]

        def value(e):
            f = 1.0 if e.source == "rule" else self.cfg.llm_factor
            return self.cfg.weights[e.tactic] * f * 0.5 ** ((now - e.t_s) / self.cfg.half_life_s)

        quotes: list[str] = []
        for e in sorted(live, key=value, reverse=True):
            if e.quote not in quotes:
                quotes.append(e.quote)
        return quotes, {e.tactic for e in live}

    def _evaluate(self, now: float, new_tactics: set[Tactic]) -> list[dict]:
        out: list[dict] = []
        level = self.risk.update_level(now)
        score = self.risk.score(now)
        if (self._last_score is None or abs(score - self._last_score) >= self.cfg.risk_emit_delta
                or level != self._last_level):
            out.append(ev.risk(self.session_id, now, self._next(), score, level,
                               self.risk.contributions(now)))
            self._last_score, self._last_level = score, level
        if self.confirmed:
            quotes, tactics = self._ranked(now)
            for act in self.counter.update(level, score, new_tactics, tactics, quotes, now):
                if act[0] == "intervention":
                    out.append(ev.intervention(self.session_id, now, self._next(), act[1], act[2]))
                else:
                    out.append(ev.alert(self.session_id, now, self._next(), act[1], act[2], act[3]))
        return out
