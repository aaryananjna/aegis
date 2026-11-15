"""scripts/ai_fixture.py: a sample call replayed labels-off with saved AI answers, for the screens."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_saved_answers_make_an_ai_fixture(tmp_path):
    answers = tmp_path / "answers.json"
    answers.write_text(json.dumps({"3": {"latency_s": 0.6, "raw": json.dumps({"tactics": [
        {"tactic": "secrecy", "utterance_id": "u3", "quote": "Please don't tell Mom"}]})}}))
    out = tmp_path / "events.jsonl"
    subprocess.run([sys.executable, str(ROOT / "scripts" / "ai_fixture.py"), str(ROOT / "examples" / "scam-grandson.call"),
                    "--out", str(out), "--answers", str(answers)], check=True, cwd=ROOT)
    evs = [json.loads(l) for l in out.read_text().splitlines()]
    assert evs[0] == {"type": "elder_set", "session_id": "example-scam-grandson", "t": 0.0,
                      "speaker_raw": None, "by": "server"}
    assert any(e["type"] == "status" and e["mode"] == "full" for e in evs)
    llm = [x for e in evs if e["type"] == "tactic_set" for x in e["evidence"] if x["source"] == "llm"]
    assert llm and llm[0]["quote"] == "Please don't tell Mom"
    assert all(e.get("speaker_raw") is None for e in evs if e["type"] == "caption")
    assert any(e["type"] == "intervention" for e in evs)
    ts = [e["t"] for e in evs]
    assert ts == sorted(ts)
