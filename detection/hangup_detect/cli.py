"""Type mode: type call lines and see what the detector does.

    c: Nana it's me, I need gift cards      (caller)
    e: Ryan? What's our code word?          (elder)

Also the fallback if the hall is too loud for live captions.
Usage: python -m hangup_detect.cli [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from .config import Config
from .pipeline import Detector
from .replay import describe
from .types import make_segment

_PREFIX = {"c": "caller", "e": "elder"}


def parse_typed(line: str) -> tuple[str, str] | None:
    head, sep, text = line.partition(":")
    who = _PREFIX.get(head.strip().lower())
    if not sep or who is None or not text.strip():
        return None
    return who, text.strip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Hang Up type mode")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    show = (lambda e: print(json.dumps(e), flush=True)) if a.json else (lambda e: print(describe(e), flush=True))
    d = Detector(Config(), "typed")
    start = time.monotonic()
    for e in d.set_elder(None, 0.0):
        show(e)
    print("Type 'c: ...' for the caller or 'e: ...' for the grandparent. Ctrl-D to end.", file=sys.stderr)
    n = 0
    for line in sys.stdin:
        parsed = parse_typed(line)
        if parsed is None:
            print("  (start the line with 'c:' or 'e:')", file=sys.stderr)
            continue
        now = time.monotonic() - start
        for e in d.tick(now) + d.feed(make_segment(f"t{n}", 0, parsed[0], parsed[1], now, now, True), now):
            show(e)
        n += 1
    for e in d.end(time.monotonic() - start):
        show(e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
