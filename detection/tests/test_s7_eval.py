from pathlib import Path

import pytest

from hangup_detect.eval import compute_metrics, load_set, run_set

ROOT = Path(__file__).resolve().parents[1]


def r(label, high_t=None, alert_t=None, onset=0.0, cid="c"):
    return {"id": cid, "label": label, "high_t": high_t, "alert_t": alert_t, "onset_s": onset}


def test_metric_math_toy_set():
    m = compute_metrics([r("scam", 5.0, 5.5, 2.0, "a"), r("scam", None, None, 1.0, "b"),
                         r("benign", 9.0, None, None, "c")])
    assert m["n_scam"] == 2 and m["n_benign"] == 1
    assert m["detected"] == 1 and m["detection_rate"] == "1/2 (50%)"
    assert m["false_alarms"] == 1 and m["false_alarm_rate"] == "1/1 (100%)"
    assert m["time_to_high"] == {"median": 3.0, "max": 3.0, "n": 1}
    assert m["time_to_alert"] == {"median": 3.5, "max": 3.5, "n": 1}
    assert m["misses"] == ["b"] and m["false_alarm_ids"] == ["c"]


def test_empty_class_is_na():
    m = compute_metrics([r("scam", 4.0, 4.0, 1.0)])
    assert m["false_alarm_rate"] == "N/A (0 benign calls)"
    m = compute_metrics([])
    assert m["detection_rate"] == "N/A (0 scam calls)"
    assert m["time_to_high"] == {"median": None, "max": None, "n": 0}


def test_scam_without_onset_rejected(tmp_path):
    (tmp_path / "x.call").write_text("# id: x\n# label: scam\n# source: synthetic\n[0-1] caller: hi\n")
    calls, rejected = load_set([tmp_path])
    assert calls == [] and "onset_s" in rejected[0][1]


def test_bad_file_rejected_with_reason(tmp_path):
    (tmp_path / "y.call").write_text("# id: y\n# label: benign\n# source: synthetic\nnope\n")
    calls, rejected = load_set([tmp_path])
    assert calls == [] and "line 4" in rejected[0][1]


def test_heldout_refuses_shared_groups(tmp_path):
    dev, held = tmp_path / "dev", tmp_path / "heldout"
    dev.mkdir()
    held.mkdir()
    body = "# id: {i}\n# label: benign\n# source: {s}\n# group: same\n[0-1] caller: hi\n"
    (dev / "a.call").write_text(body.format(i="a", s="synthetic"))
    (held / "b.call").write_text(body.format(i="b", s="team-staged"))
    with pytest.raises(SystemExit, match="group"):
        run_set("heldout", root=tmp_path)


def test_dev_set_runs_and_reports():
    m = run_set("dev", root=ROOT / "eval" / "calls")
    assert m["n_scam"] == 21 and m["n_benign"] == 21
    assert m["rejected"] == []
    assert m["latency_ms"]["n"] > 0


def test_report_does_not_credit_claude_for_heldout_calls():
    # Held-out calls are written by the team, outside the detector's tuning.
    m = {"set": "heldout", "sources": ["synthetic"], "n_scam": 1, "n_benign": 1,
         "detection_rate": "1/1", "false_alarm_rate": "0/1",
         "time_to_high": {"median": 1, "max": 1, "n": 1}, "time_to_alert": {"median": 1, "max": 1, "n": 1},
         "latency_ms": {"median": 0.1, "p95": 0.1}, "misses": [], "false_alarm_ids": [], "rejected": []}
    from hangup_detect.eval import report
    head = report(m, False).splitlines()[0]
    assert "Claude" not in head and "team" in head
