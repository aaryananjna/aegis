"""Noisy-hall fallback: type the call and it reaches the screens as "typed" captions.

    python tools/dev_server/typed_cli.py              # starts a new session, prints the links
    python tools/dev_server/typed_cli.py <session_id> # types into an existing session

Lines:  c: Grandma, it's me         (caller, speaker_raw "1")
        e: Who is this?             (grandparent, speaker_raw "0")
        end                         (ends the call)
Then tap "Voice 1"/"Voice 2" on /elder as usual: the grandparent is the "e:" voice.
Only standard library; works against tools/dev_server on the same laptop.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

BASE = os.environ.get("AEGIS_SERVER", "http://localhost:8000")
SPEAKER = {"c": "1", "e": "0"}


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(BASE + path, json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.load(r)


def main(argv: list[str]) -> int:
    if argv:
        sid = argv[0]
    else:
        s = post("/sessions", {"name": "Rose"})
        sid = s["session_id"]
        print(f"elder:  {s['elder_url']}\nfamily: {s['family_url']}")
    print("Type 'c: ...' for the caller, 'e: ...' for the grandparent, 'end' to finish.",
          file=sys.stderr)
    for line in sys.stdin:
        line = line.strip()
        if line == "end":
            post(f"/sessions/{sid}/end", {})
            break
        who, sep, text = line.partition(":")
        if not sep or who.strip().lower() not in SPEAKER or not text.strip():
            print("  (start the line with 'c:' or 'e:')", file=sys.stderr)
            continue
        post("/typed", {"session_id": sid, "text": text.strip(),
                        "speaker_raw": SPEAKER[who.strip().lower()]})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
