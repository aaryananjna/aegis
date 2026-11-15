"""Build a sample-call event file for the screens with the AI layer on, labels off (demo mode).

    python scripts/ai_fixture.py examples/scam-grandson.call --out fixtures/events-scam-grandson-ai.jsonl

Without --answers it asks Groq live (GROQ_API_KEY from detection/.env) and saves every answer
to <out>.answers.json, so the file can be rebuilt later without calling the API:

    python scripts/ai_fixture.py examples/scam-grandson.call --out ... --answers <out>.answers.json

Every AI answer in the file is a real answer from the model; nothing is written by hand.
Answers are keyed by the caption index that triggered the request and land latency_s later.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hangup_detect.config import Config  # noqa: E402
from hangup_detect.llm import build_messages  # noqa: E402
from hangup_detect.pipeline import Detector  # noqa: E402
from hangup_detect.replay import _caption, _strip_speaker, parse_call  # noqa: E402

CAPTION_DELAY_S = 0.5


def live_asker():
    from hangup_detect.llm_runner import http_transport
    env = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("\"'")
    call = http_transport(env)

    def ask(req):
        t0 = time.perf_counter()
        raw = call("groq", build_messages(req.utterances, mixed=req.mixed), 5.0)
        return {"latency_s": round(time.perf_counter() - t0, 2), "raw": raw}
    return ask


def build(call, answers: dict | None) -> tuple[list[dict], dict]:
    sid = call.headers["id"]
    d = Detector(Config(), sid)
    out: list[dict] = [{"type": "elder_set", "session_id": sid, "t": 0.0, "speaker_raw": None, "by": "server"}]
    out += d.set_elder(None, 0.0)
    segs = [_strip_speaker(s) for s in call.lines]
    ask = None if answers is not None else live_asker()
    used: dict = {}
    timeline = [(s.end_s + CAPTION_DELAY_S, 0, i) for i, s in enumerate(segs)]
    last = max(t for t, _, _ in timeline)
    timeline += [(float(t), 1, -1) for t in range(1, math.ceil(last) + 3)]
    timeline.sort()
    pending: list[tuple[float, int, str]] = []
    for at, kind, i in timeline:
        for p in sorted(x for x in pending if x[0] <= at):
            pending.remove(p)
            out += d.llm_status("full", p[0])
            out += d.apply_llm(p[1], p[2], p[0])
        if kind == 0:
            out.append(_caption(sid, segs[i], at))
            out += d.feed(segs[i], at)
            req = d.llm_request(at)
            if req is None:
                continue
            ans = answers.get(str(i)) if answers is not None else ask(req)
            if ans is None:
                continue
            used[str(i)] = ans
            pending.append((round(at + ans["latency_s"], 3), req.seq, ans["raw"]))
        else:
            out += d.tick(at)
    out += d.end(last + 2)
    out.sort(key=lambda e: e["t"])  # stable: same-time events keep their order
    return out, used


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("call")
    ap.add_argument("--out", required=True)
    ap.add_argument("--answers", help="saved answers JSON; omit to ask Groq live and save them")
    a = ap.parse_args()
    answers = json.loads(Path(a.answers).read_text()) if a.answers else None
    events, used = build(parse_call(Path(a.call).read_text()), answers)
    out = Path(a.out)
    out.write_text("".join(json.dumps(e) + "\n" for e in events))
    if answers is None:
        Path(str(out) + ".answers.json").write_text(json.dumps(used, indent=1) + "\n")
    print(f"wrote {len(events)} events to {out}" + ("" if answers else f" (+ {len(used)} saved answers)"))


if __name__ == "__main__":
    main()
