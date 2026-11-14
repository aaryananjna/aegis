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
from .guard import parse_llm
from .rules import find_evidence
from .types import Evidence, LLMRequest, Segment, Tactic, speaker_id

LLM_WINDOW_S = 60.0
MAX_LLM_REQUESTS = 16


class Detector:
    def __init__(self, config: Config, session_id: str):
        self.cfg = config.validate()
        self.session_id = session_id
        self.risk = RiskModel(self.cfg)
        self.counter = CounterMoves(self.cfg)
        self.elder_raw: str | None = None
        self.confirmed = False  # set by set_elder; cards and alerts wait for it
        self.ended = False
        self._seq = 0
        self._now = 0.0
        self._last_rev: dict[str, int] = {}
        self._finals: OrderedDict[str, tuple[Segment, float]] = OrderedDict()
        self._shown: dict[str, list[dict]] = {}  # utterance_id -> evidence C currently shows
        self._last_score: float | None = None
        self._last_level = "low"
        self._timing: list[dict] = []
        # AI layer state (S8a)
        self._mode = "rules_only"
        self._llm_seq = 0
        self._llm_last_s: float | None = None
        self._llm_requests: OrderedDict[int, LLMRequest] = OrderedDict()
        self._llm_evidence: list[Evidence] = []
        self._llm_seen: set[tuple[Tactic, str]] = set()
        self._llm_dirty = False  # a new caller line arrived since the last request

    # ---- public API -----------------------------------------------------
    def feed(self, seg: Segment, now_s: float) -> list[dict]:
        now = self._clock(now_s)
        uid = seg.utterance_id
        if uid in self._finals:
            return [self._status("duplicate final ignored")] if seg.is_final else []
        last = self._last_rev.get(uid)
        if last is not None and (seg.revision < last or (seg.revision == last and not seg.is_final)):
            return []  # stale revision (a final may reuse the last interim's revision)
        self._last_rev[uid] = seg.revision
        if not seg.is_final:
            # Highlight words while they're still being spoken. Never scores.
            return self._set_highlights(seg, self._hits(seg, now), True, now)

        out: list[dict] = []
        self._finals[uid] = (seg, now)
        if len(self._finals) > self.cfg.max_finals:
            self._finals.popitem(last=False)
            out.append(self._status("oldest caption dropped from the rebuild store"))
        hits = self._score_final(seg, now)
        if self._role(seg) != "elder":
            self._llm_dirty = True
        out += self._set_highlights(seg, hits, False, now)
        new_tactics = {h.tactic for h in hits}
        self._timing.append({"utterance_id": uid, "end_s": seg.end_s, "arrival_s": now,
                             "tactics": sorted(t.value for t in new_tactics)})
        return out + self._evaluate(now, new_tactics)

    def tick(self, now_s: float) -> list[dict]:
        return self._evaluate(self._clock(now_s), set())

    def set_elder(self, speaker_raw: str | int | None, now_s: float) -> list[dict]:
        """Confirm who the grandparent is (None = no speaker labels) and rebuild the evidence."""
        now = self._clock(now_s)
        self.elder_raw = speaker_id(speaker_raw)
        self.confirmed = True
        self.risk.clear()
        out: list[dict] = []
        for uid, (seg, arrival) in self._finals.items():
            hits = self._score_final(seg, arrival)
            llm = [] if self._role(seg) == "elder" else [e for e in self._llm_evidence if e.utterance_id == uid]
            self.risk.evidence.extend(llm)
            out += self._set_highlights(seg, hits + llm, False, now)
        self._last_score = None  # force a fresh risk event
        return out + self._evaluate(now, set())

    # ---- AI layer (S8a) ---------------------------------------------------
    def llm_request(self, now_s: float) -> LLMRequest | None:
        """Lines from the last 60 s to send to the AI layer, or None.

        Labels on: off until the grandparent tap names a speaker, then caller lines only.
        Labels off (set_elder(None), one shared mic): off until the rules flag something in
        the window, then both voices go mixed and the AI works out which lines are the
        caller's (config.llm_mixed). Only asks again once a new line has arrived.
        """
        now = self._clock(now_s)
        if not (self.confirmed and self._llm_dirty):
            return None
        if self._llm_last_s is not None and now - self._llm_last_s < self.cfg.llm_min_interval_s:
            return None  # too soon; the next request still covers the last 60 s
        mixed = self.elder_raw is None
        if mixed:
            window = {uid for uid, (seg, arrival) in self._finals.items() if now - arrival < LLM_WINDOW_S}
            if not (self.cfg.llm_mixed and (self.cfg.llm_mixed_always or any(
                    e.source == "rule" and e.utterance_id in window for e in self.risk.evidence))):
                return None
        utts = tuple((uid, seg.text) for uid, (seg, arrival) in self._finals.items()
                     if now - arrival < LLM_WINDOW_S
                     and (self._role(seg) != "elder" if mixed else self._role(seg) == "caller"))
        if not utts:
            return None
        self._llm_dirty = False
        self._llm_last_s = now
        self._llm_seq += 1
        req = LLMRequest(self._llm_seq, utts, now, mixed)
        self._llm_requests[req.seq] = req
        while len(self._llm_requests) > MAX_LLM_REQUESTS:
            self._llm_requests.popitem(last=False)
        return req

    def apply_llm(self, seq: int, raw: str, now_s: float) -> list[dict]:
        """Add the AI layer's answer for request `seq`. Each request applies once.

        Only checked, quoted, add-only evidence gets in. A repeat of a tactic the AI already
        flagged on the same line (from an overlapping window) is skipped.
        """
        now = self._clock(now_s)
        req = self._llm_requests.pop(seq, None)
        if req is None:
            return []
        hits = [h for h in parse_llm(raw, dict(req.utterances), now)
                if h.utterance_id in self._finals
                and self._role(self._finals[h.utterance_id][0]) != "elder"
                and (h.tactic, h.utterance_id) not in self._llm_seen]
        if not hits:
            return []
        for h in hits:
            self._llm_seen.add((h.tactic, h.utterance_id))
            self._llm_evidence.append(h)
            self.risk.evidence.append(h)
        out: list[dict] = []
        for uid in dict.fromkeys(h.utterance_id for h in hits):
            both = [e for e in self.risk.evidence if e.utterance_id == uid]
            out += self._set_highlights(self._finals[uid][0], both, False, now)
        return out + self._evaluate(now, set())  # only rule dodges escalate cards

    def llm_status(self, mode: str, now_s: float, warning: str | None = None) -> list[dict]:
        """Tell the screens when the AI layer turns on ("full") or off ("rules_only")."""
        self._clock(now_s)
        if mode == self._mode:
            return []
        self._mode = mode
        return [ev.status(self.session_id, self._now, self._next(), mode, warning)]

    def codeword_result(self, ok: bool, now_s: float) -> list[dict]:
        """The elder screen says whether the caller gave the right family code word (C12).

        `ok` must be a real bool. Anything else ("false", 0, None) raises TypeError rather than
        being read as truthy, which would wrongly switch off the hang up card (issue #10).
        """
        if not isinstance(ok, bool):
            raise TypeError(f"codeword_result ok must be True or False, got {type(ok).__name__}")
        now = self._clock(now_s)
        if self.counter.state != "codeword":
            return [self._status("codeword_result ignored: no code word card showing")]
        quotes, tactics = self._ranked(now)
        return self._actions(self.counter.codeword_result(ok, quotes, tactics, now), now)

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
    def _hits(self, seg: Segment, t: float) -> list[Evidence]:
        """Rule evidence for a caption, or nothing if the grandparent said it."""
        return [] if self._role(seg) == "elder" else find_evidence(seg.text, seg.utterance_id, t)

    def _score_final(self, seg: Segment, t: float) -> list[Evidence]:
        hits = self._hits(seg, t)
        self.risk.evidence.extend(hits)
        return hits

    def _clock(self, now_s: float) -> float:
        if self.ended:
            raise RuntimeError("detector has ended; start a new session")
        self._now = max(self._now, float(now_s))
        return self._now

    def _next(self) -> int:
        self._seq += 1
        return self._seq

    def _status(self, warning: str) -> dict:
        return ev.status(self.session_id, self._now, self._next(), self._mode, warning)

    def _role(self, seg: Segment) -> str:
        if self.confirmed and self.elder_raw is not None and seg.speaker_raw is not None:
            return "elder" if seg.speaker_raw == self.elder_raw else "caller"
        return seg.speaker

    def _set_highlights(self, seg: Segment, hits: list[Evidence], provisional: bool, now: float) -> list[dict]:
        uid = seg.utterance_id
        if not hits and not self._shown.get(uid):
            return []
        evidence = [h.as_dict() for h in hits]
        self._shown[uid] = evidence
        return [ev.tactic_set(self.session_id, now, self._next(), uid, seg.revision, provisional, evidence)]

    def _ranked(self, now: float) -> tuple[list[str], set[Tactic]]:
        live = self.risk.live(now)
        ranked = sorted(live, key=lambda e: self.risk.value(e, now), reverse=True)
        return list(dict.fromkeys(e.quote for e in ranked)), {e.tactic for e in live}

    def _evaluate(self, now: float, new_tactics: set[Tactic]) -> list[dict]:
        out: list[dict] = []
        level, score, contributions = self.risk.evaluate(now)
        if (self._last_score is None or abs(score - self._last_score) >= self.cfg.risk_emit_delta
                or level != self._last_level):
            out.append(ev.risk(self.session_id, now, self._next(), score, level, contributions))
            self._last_score, self._last_level = score, level
        if self.confirmed and self.counter.state != "hangup":  # hangup is the last card
            quotes, tactics = self._ranked(now)
            family = any(e.tactic is Tactic.IMPERSONATION and e.detail == "family"
                         for e in self.risk.live(now))
            out += self._actions(self.counter.update(level, score, new_tactics, tactics, quotes, now, family), now)
        return out

    def _actions(self, acts: list[tuple], now: float) -> list[dict]:
        out = []
        for act in acts:
            if act[0] == "codeword_ok":
                out.append(ev.codeword_ok(self.session_id, now, self._next()))
            elif act[0] == "intervention":
                out.append(ev.intervention(self.session_id, now, self._next(), act[1], act[2]))
            else:
                out.append(ev.alert(self.session_id, now, self._next(), act[1], act[2], act[3]))
        return out
