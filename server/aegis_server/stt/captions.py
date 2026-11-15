"""Deepgram streaming results -> CONTRACTS `caption` events. Pure logic, no network.

How Deepgram streams: while someone talks it sends interim results for the current stretch of
audio, each replacing the last, then one `is_final` result for that stretch. Then the next
stretch starts. With diarize on, each word carries a `speaker` number.

How that maps to captions:
- One stretch of audio is split into lines: a new line when the speaker changes or a sentence
  ends (., ?, !; not after titles like "Dr."). Each line is one caption with utterance_id
  `u<stretch>-<line>`.
- `revision` counts results within the stretch, so every interim update has a higher revision.
- When the final for a stretch comes, every run gets `is_final: true`. A run that existed in an
  interim but not in the final (Deepgram re-split the speakers) is closed with an empty final,
  so no stale interim line stays on screen.
- No speaker numbers (diarize off, or a model without it) -> `speaker_raw: null`, which C's elder
  screen shows as "This call doesn't show who is talking".
- `offset_s` shifts times after a reconnect, since Deepgram's clock restarts at 0.
"""
from __future__ import annotations

from typing import Any


def _speaker(word: dict) -> str | None:
    s = word.get("speaker")
    return None if s is None else str(s)


# Titles Deepgram writes with a dot that don't end a sentence.
_TITLES = {"dr.", "mr.", "mrs.", "ms.", "st.", "jr.", "sr.", "mt.", "vs."}


def _ends_sentence(word: dict) -> bool:
    w = (word.get("punctuated_word") or "").strip()
    if not w or w.lower() in _TITLES:
        return False
    return w[-1] in ".?!" or w.endswith(('."', '?"', '!"'))


def _runs(words: list[dict]) -> list[tuple[str | None, list[dict]]]:
    """Split into caption lines: a new line on a speaker change or after a sentence ends.

    Without speaker labels (the demo) one stretch of audio can hold several people's
    sentences back to back, so cutting at sentence ends keeps lines short and readable.
    """
    runs: list[tuple[str | None, list[dict]]] = []
    cut = False
    for w in words:
        spk = _speaker(w)
        if runs and runs[-1][0] == spk and not cut:
            runs[-1][1].append(w)
        else:
            runs.append((spk, [w]))
        cut = _ends_sentence(w)
    return runs


def _text(words: list[dict]) -> str:
    return " ".join(w.get("punctuated_word") or w.get("word", "") for w in words).strip()


class CaptionMaker:
    def __init__(self, session_id: str, source: str = "live") -> None:
        self.session_id = session_id
        self.source = source
        self.offset_s = 0.0
        self._stretch = 0          # which stretch of audio we're in
        self._revision = 0         # results seen in this stretch
        self._open: dict[str, dict] = {}  # utterance_id -> last caption sent, not final yet

    def feed(self, msg: dict[str, Any]) -> list[dict]:
        """One Deepgram message -> zero or more caption events, in order."""
        if msg.get("type") != "Results":
            return []
        alts = (msg.get("channel") or {}).get("alternatives") or [{}]
        words = alts[0].get("words") or []
        is_final = bool(msg.get("is_final"))
        if not words and not is_final:
            return []

        self._revision += 1
        out: list[dict] = []
        seen: set[str] = set()
        for k, (spk, run) in enumerate(_runs(words)):
            uid = f"u{self._stretch}-{k}"
            seen.add(uid)
            cap = self._caption(uid, spk, _text(run), run[0].get("start", 0.0),
                                run[-1].get("end", 0.0), is_final)
            out.append(cap)
            if not is_final:
                self._open[uid] = cap
        if is_final:
            # Close lines from earlier interims that the final no longer has.
            for uid, old in self._open.items():
                if uid not in seen:
                    out.append({**old, "revision": self._revision, "text": "",
                                "is_final": True})
            self._open.clear()
            self._stretch += 1
            self._revision = 0
        return out

    def close_open(self) -> list[dict]:
        """Finals for anything still interim (stream ended or dropped mid-sentence)."""
        out = [{**c, "revision": c["revision"] + 1, "is_final": True}
               for c in self._open.values()]
        self._open.clear()
        if out:
            self._stretch += 1
            self._revision = 0
        return out

    def _caption(self, uid: str, spk: str | None, text: str, start: float, end: float,
                 is_final: bool) -> dict:
        start_s = round(max(0.0, float(start) + self.offset_s), 3)
        end_s = round(max(start_s, float(end) + self.offset_s), 3)
        return {"type": "caption", "session_id": self.session_id, "utterance_id": uid,
                "revision": self._revision, "speaker_raw": spk, "text": text,
                "start_s": start_s, "end_s": end_s, "is_final": is_final,
                "source": self.source}
