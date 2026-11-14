"""Check the AI layer's answer before any of it counts.

This is provenance only: a quote must really appear, as whole words, in the caller line it
names. It does not prove the tactic is right. Safety comes from the rest of the design:
AI evidence is add-only, capped at +1.5 and can never make the level HIGH on its own.
"""
from __future__ import annotations

import json
import re

from .types import Evidence, Tactic

MAX_BYTES = 16 * 1024
MAX_ITEMS = 8
MIN_WORDS, MAX_WORDS = 2, 30
_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'"})
_TACTICS = {t.value: t for t in Tactic}


def parse_llm(raw: str, utterances: dict[str, str], t_s: float) -> list[Evidence]:
    """Turn the model's JSON into Evidence, dropping anything that doesn't check out."""
    if not isinstance(raw, str) or len(raw.encode("utf-8", "ignore")) > MAX_BYTES:
        return []
    try:
        obj = json.loads(raw)
    except (ValueError, RecursionError):  # deep nesting raises RecursionError on older Pythons
        return []
    items = obj.get("tactics") if isinstance(obj, dict) else None
    if not isinstance(items, list):
        return []
    out: list[Evidence] = []
    seen: set[tuple[Tactic, str]] = set()
    for item in items[:MAX_ITEMS]:
        if not isinstance(item, dict):
            continue
        tactic, uid, quote = item.get("tactic"), item.get("utterance_id"), item.get("quote")
        if not all(isinstance(x, str) for x in (tactic, uid, quote)):
            continue
        if tactic not in _TACTICS or uid not in utterances:
            continue
        words = quote.translate(_APOSTROPHES).split()
        if not MIN_WORDS <= len(words) <= MAX_WORDS:
            continue
        span = _find(utterances[uid], words)
        key = (_TACTICS[tactic], uid)
        if span is None or key in seen:
            continue
        seen.add(key)
        text = utterances[uid]
        out.append(Evidence(_TACTICS[tactic], text[span[0]:span[1]], uid, span, "llm", t_s))
    return out


def _find(text: str, words: list[str]) -> tuple[int, int] | None:
    """Whole-word, case-insensitive match; same-length normalization keeps spans valid."""
    pattern = r"(?<!\w)" + r"\s+".join(re.escape(w) for w in words) + r"(?!\w)"
    m = re.search(pattern, text.translate(_APOSTROPHES), re.IGNORECASE)
    return (m.start(), m.end()) if m else None
