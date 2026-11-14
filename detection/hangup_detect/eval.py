"""Honest numbers: run labeled calls through the exact demo pipeline.

    python -m hangup_detect.eval --set dev        # synthetic calls we tune on
    python -m hangup_detect.eval --set heldout    # staged calls A and C wrote; judge-facing numbers

Detection = scam calls that reached HIGH. False alarm = benign calls that reached HIGH.
Times are measured from each scam call's annotated onset_s.
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

from .replay import parse_call, replay

CALLS_ROOT = Path(__file__).resolve().parents[1] / "eval" / "calls"


def load_set(dirs: list[Path]):
    calls, rejected = [], []
    for d in dirs:
        for f in sorted(Path(d).glob("*.call")):
            try:
                call = parse_call(f.read_text(encoding="utf-8"))
                if call.headers["label"] == "scam" and call.onset_s is None:
                    raise ValueError("scam calls need '# onset_s:'")
            except ValueError as exc:
                rejected.append((f.name, str(exc)))
                continue
            calls.append(call)
    return calls, rejected


def _rate(k: int, n: int, what: str) -> str:
    return f"N/A (0 {what} calls)" if n == 0 else f"{k}/{n} ({round(100 * k / n)}%)"


def _stats(xs: list[float]) -> dict:
    if not xs:
        return {"median": None, "max": None, "n": 0}
    return {"median": round(statistics.median(xs), 2), "max": round(max(xs), 2), "n": len(xs)}


def compute_metrics(results: list[dict]) -> dict:
    scam = [r for r in results if r["label"] == "scam"]
    benign = [r for r in results if r["label"] == "benign"]
    hit = [r for r in scam if r["high_t"] is not None]
    fa = [r for r in benign if r["high_t"] is not None]
    return {
        "n_scam": len(scam), "n_benign": len(benign),
        "detected": len(hit), "detection_rate": _rate(len(hit), len(scam), "scam"),
        "false_alarms": len(fa), "false_alarm_rate": _rate(len(fa), len(benign), "benign"),
        "time_to_high": _stats([r["high_t"] - r["onset_s"] for r in hit]),
        "time_to_alert": _stats([r["alert_t"] - r["onset_s"] for r in hit if r["alert_t"] is not None]),
        "misses": [r["id"] for r in scam if r["high_t"] is None],
        "false_alarm_ids": [r["id"] for r in fa],
    }


def run_calls(calls, no_speakers=False):
    results, feed_ms = [], []
    for call in calls:
        evs = replay(call, no_speakers=no_speakers, feed_ms=feed_ms)
        high = next((e["t"] for e in evs if e["type"] == "risk" and e["level"] == "high"), None)
        alert = next((e["t"] for e in evs if e["type"] == "alert"), None)
        results.append({"id": call.headers["id"], "label": call.headers["label"],
                        "high_t": high, "alert_t": alert, "onset_s": call.onset_s})
    return results, feed_ms


def run_set(name: str, root: Path = CALLS_ROOT, no_speakers: bool = False) -> dict:
    dirs = {"dev": [root / "dev"], "heldout": [root / "heldout"],
            "all": [root / "dev", root / "heldout"]}[name]
    calls, rejected = load_set(dirs)
    if name == "heldout":
        dev_calls, _ = load_set([root / "dev"])
        shared = {c.headers.get("group") for c in calls} & {c.headers.get("group") for c in dev_calls}
        shared.discard(None)
        if shared:
            raise SystemExit(f"refusing: held-out calls share a script group with dev: {sorted(shared)}")
    results, feed_ms = run_calls(calls, no_speakers)
    m = compute_metrics(results)
    ms = sorted(feed_ms)
    m["latency_ms"] = {"median": round(statistics.median(ms), 3) if ms else None,
                       "p95": round(ms[int(0.95 * (len(ms) - 1))], 3) if ms else None, "n": len(ms)}
    m["rejected"] = rejected
    m["sources"] = sorted({c.headers["source"] for c in calls})
    m["set"] = name
    return m


def report(m: dict, no_speakers: bool) -> str:
    src = ", ".join(m["sources"]) or "no calls"
    kind = "synthetic, written by Claude" if m["sources"] == ["synthetic"] else src
    lines = [
        f"Set: {m['set']} ({kind}). {m['n_scam']} scam + {m['n_benign']} benign calls."
        + (" Speaker labels ignored." if no_speakers else ""),
        f"  Caught (reached HIGH):     {m['detection_rate']}",
        f"  False alarms:              {m['false_alarm_rate']}",
        f"  Time to HIGH from onset:   median {m['time_to_high']['median']} s, max {m['time_to_high']['max']} s (n={m['time_to_high']['n']})",
        f"  Time to family alert:      median {m['time_to_alert']['median']} s, max {m['time_to_alert']['max']} s (n={m['time_to_alert']['n']})",
        f"  Processing per caption:    median {m['latency_ms']['median']} ms, p95 {m['latency_ms']['p95']} ms",
        f"  Missed scams:              {', '.join(m['misses']) or 'none'}",
        f"  False alarm calls:         {', '.join(m['false_alarm_ids']) or 'none'}",
    ]
    for name, why in m["rejected"]:
        lines.append(f"  REJECTED {name}: {why}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Aegis eval")
    ap.add_argument("--set", choices=["dev", "heldout", "all"], default="dev")
    ap.add_argument("--no-speakers", action="store_true")
    a = ap.parse_args(argv)
    m = run_set(a.set, no_speakers=a.no_speakers)
    print(report(m, a.no_speakers))
    return 1 if m["rejected"] else 0


if __name__ == "__main__":
    sys.exit(main())
