"""Event builders. Must match CONTRACTS.md exactly."""
from __future__ import annotations


def _base(kind: str, session_id: str, t: float, seq: int) -> dict:
    return {"type": kind, "session_id": session_id, "t": round(t, 3), "seq": seq}


def tactic_set(session_id, t, seq, utterance_id, revision, provisional, evidence):
    return {**_base("tactic_set", session_id, t, seq), "utterance_id": utterance_id,
            "revision": revision, "provisional": provisional, "evidence": evidence}


def risk(session_id, t, seq, score, level, contributions):
    return {**_base("risk", session_id, t, seq), "score": round(score, 4),
            "level": level, "contributions": contributions}


def intervention(session_id, t, seq, kind, text):
    return {**_base("intervention", session_id, t, seq), "kind": kind,
            "text": text, "latched": kind != "none"}


def alert(session_id, t, seq, kind, evidence, summary):
    return {**_base("alert", session_id, t, seq), "alert_id": f"{session_id}:{kind}",
            "kind": kind, "evidence": evidence, "summary": summary}


def status(session_id, t, seq, mode, warning=None):
    return {**_base("status", session_id, t, seq), "mode": mode, "warning": warning}
