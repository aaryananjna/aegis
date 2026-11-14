"""Replay a .call file through the exact detector the demo uses.

Format:
    # id: some-id                 (required)
    # label: scam | benign        (required)
    # source: synthetic | team-staged   (required)
    # set: dev | heldout | example
    # group: script-family
    # onset_s: 3.0                (scam calls: when the first scam move happens)
    # elder: 0                    (optional: raw id of the grandparent for spkN lines)
    [1.8-4.6] spk1: Nana, it's me.
Speakers: caller, elder, or spkN (a raw diarized voice id N).

Usage: python -m hangup_detect.replay file.call [--elder 0] [--json] [--realtime]
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import re
import sys
import time
from dataclasses import dataclass, field

from .config import Config
from .pipeline import Detector
from .types import Segment, make_segment

_LINE = re.compile(r"^\[(?P<s>[\d.]+)-(?P<e>[\d.]+)\]\s*(?P<who>caller|elder|spk\d+):\s*(?P<text>.*)$")
_HEADER = re.compile(r"^#\s*(?P<k>[a-z_]+):\s*(?P<v>.*?)(?:\s+#.*)?$")  # trailing "# note" ignored
LABELS = {"scam", "benign"}
SOURCES = {"synthetic", "team-staged"}


@dataclass
class Call:
    headers: dict[str, str]
    lines: list[Segment] = field(default_factory=list)

    @property
    def onset_s(self) -> float | None:
        v = self.headers.get("onset_s")
        return float(v) if v else None

    @property
    def elder(self) -> str | None:
        return self.headers.get("elder")


def parse_call(text: str) -> Call:
    headers: dict[str, str] = {}
    lines: list[Segment] = []
    for n, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            m = _HEADER.match(line)
            if m:
                headers[m["k"]] = m["v"].strip()
            continue
        m = _LINE.match(line)
        if not m:
            raise ValueError(f"line {n}: expected '[start-end] caller|elder|spkN: text', got {raw!r}")
        who = m["who"]
        speaker, raw_id = (who, None) if who in ("caller", "elder") else ("unknown", who[3:])
        try:
            seg = make_segment(f"u{len(lines)}", 0, speaker, m["text"], float(m["s"]), float(m["e"]),
                               True, speaker_raw=raw_id)
        except ValueError as exc:
            raise ValueError(f"line {n}: {exc}") from None
        lines.append(seg)
    for key, allowed in (("label", LABELS), ("source", SOURCES)):
        if headers.get(key) not in allowed:
            raise ValueError(f"header '# {key}:' must be one of {sorted(allowed)}")
    if "id" not in headers:
        raise ValueError("header '# id:' is required")
    return Call(headers, lines)


def replay(call: Call, elder: str | None = None, confirm: bool = True, caption_delay_s: float = 0.5,
           no_speakers: bool = False, config: Config | None = None, realtime: bool = False,
           on_event=None, feed_ms: list[float] | None = None, captions: bool = False) -> list[dict]:
    """Feed finals at end_s + caption_delay_s, tick every 1.0 s, then end.

    captions=True also emits the `caption` event A's server would forward for each line,
    just before the detector's events for it, so C can build screens from fixtures.
    """
    if elder is None:
        elder = call.elder
    d = Detector(config or Config(), call.headers["id"])
    out: list[dict] = []

    def emit(evs):
        for e in evs:
            out.append(e)
            if on_event:
                on_event(e)

    if confirm:
        emit(d.set_elder(None if no_speakers else elder, 0.0))
    segs = [_strip_speaker(s) if no_speakers else s for s in call.lines]
    # (time, kind, index): captions (kind 0) before the tick (kind 1) at the same time
    timeline = [(s.end_s + caption_delay_s, 0, i) for i, s in enumerate(segs)]
    last = max((t for t, _, _ in timeline), default=0.0)
    timeline += [(float(t), 1, -1) for t in range(1, math.ceil(last) + 1)]
    timeline.sort()
    started = time.monotonic()
    for at, kind, i in timeline:
        if realtime:
            time.sleep(max(0.0, at - (time.monotonic() - started)))
        if kind == 0:
            if captions:
                emit([_caption(call.headers["id"], segs[i], at)])
            t0 = time.perf_counter()
            evs = d.feed(segs[i], at)
            if feed_ms is not None:
                feed_ms.append((time.perf_counter() - t0) * 1000)
            emit(evs)
        else:
            emit(d.tick(at))
    emit(d.end(last))
    return out


def _caption(session_id: str, s: Segment, t: float) -> dict:
    """The caption event as A sends it (CONTRACTS.md), plus t. No seq: that orders B's events only."""
    return {"type": "caption", "session_id": session_id, "t": round(t, 3),
            "utterance_id": s.utterance_id, "revision": s.revision, "speaker_raw": s.speaker_raw,
            "text": s.text, "start_s": s.start_s, "end_s": s.end_s, "is_final": s.is_final}


def _strip_speaker(s: Segment) -> Segment:
    return dataclasses.replace(s, speaker="unknown", speaker_raw=None)


def describe(e: dict) -> str:
    """One readable line per event, for the terminal."""
    t = f"{e['t']:6.1f}s"
    if e["type"] == "caption":
        return f"{t}  caption  [{e['speaker_raw'] or '?'}] {e['text']}"
    if e["type"] == "tactic_set":
        tag = "~" if e["provisional"] else " "
        hits = ", ".join(f"{x['tactic']}: \"{x['quote']}\"" for x in e["evidence"]) or "(cleared)"
        return f"{t} {tag}tactics  {hits}"
    if e["type"] == "risk":
        return f"{t}  risk     {e['score']:.2f} {e['level'].upper()}"
    if e["type"] == "intervention":
        return f"{t}  CARD     {e['text']}"
    if e["type"] == "alert":
        return f"{t}  ALERT    {e['summary']} {e['evidence']}"
    return f"{t}  status   {e['mode']} {e.get('warning') or ''}".rstrip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--elder", help="raw speaker id of the grandparent, e.g. 0")
    ap.add_argument("--json", action="store_true", help="print JSON lines")
    ap.add_argument("--realtime", action="store_true")
    ap.add_argument("--no-speakers", action="store_true", help="ignore speaker labels")
    ap.add_argument("--captions", action="store_true", help="also print caption events, like A sends")
    a = ap.parse_args(argv)
    try:
        with open(a.file, encoding="utf-8") as f:
            call = parse_call(f.read())
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    show = (lambda e: print(json.dumps(e))) if a.json else (lambda e: print(describe(e)))
    replay(call, elder=a.elder, no_speakers=a.no_speakers, realtime=a.realtime, on_event=show,
           captions=a.captions)
    return 0


if __name__ == "__main__":
    sys.exit(main())
