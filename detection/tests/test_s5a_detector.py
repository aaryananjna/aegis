import pytest

from hangup_detect.config import Config
from hangup_detect.pipeline import Detector
from hangup_detect.types import make_segment

SCAM = ["Nana it's me, I got in an accident",
        "Please don't tell Mom, I need Google Play gift cards right now"]


def seg(uid, text, speaker="caller", rev=0, final=True, raw=None, t=0.0):
    return make_segment(uid, rev, speaker, text, t, t + 1.0, final, speaker_raw=raw)


def run(d, lines, speaker="caller", raw=None, start=0.0, prefix="u"):
    out = []
    for i, text in enumerate(lines):
        out += d.feed(seg(f"{prefix}{i}", text, speaker, raw=raw, t=start + i * 3), start + i * 3 + 1.5)
    return out


def kinds(evs, k):
    return [e for e in evs if e["type"] == k]


def confirmed(**kw):
    d = Detector(Config(), "s1", **kw)
    d.set_elder(None, 0.0)
    return d


def test_scam_reaches_high_and_shows_codeword():
    d = confirmed()
    evs = run(d, SCAM)
    assert kinds(evs, "risk")[-1]["level"] == "high"
    assert [e["kind"] for e in kinds(evs, "intervention")] == ["codeword"]
    assert kinds(evs, "alert")[0]["alert_id"] == "s1:codeword"
    assert kinds(evs, "tactic_set")[0]["provisional"] is False


def test_elder_never_scores():
    d = confirmed()
    evs = run(d, SCAM, speaker="elder")
    assert kinds(evs, "tactic_set") == [] and kinds(evs, "intervention") == []
    assert d.state()["score"] < 0.06


def test_elder_by_raw_mapping():
    d = Detector(Config(), "s1")
    d.set_elder("0", 0.0)
    run(d, SCAM, speaker="unknown", raw="0")
    assert d.state()["level"] == "low"
    run(d, SCAM, speaker="unknown", raw="1", start=20.0, prefix="v")
    assert d.state()["level"] == "high"


def test_unknown_scores_like_caller():
    d = confirmed()
    run(d, SCAM, speaker="unknown")
    assert d.state()["level"] == "high"


def test_duplicate_final_stale_revision_and_late_interim_ignored():
    d = confirmed()
    d.feed(seg("u1", "I need gift cards", rev=2, final=False), 1.0)
    assert d.feed(seg("u1", "I need gift cards", rev=1, final=False), 1.1) == []
    d.feed(seg("u1", "I need gift cards", rev=3), 1.2)
    score = d.risk.score(1.2)
    dup = d.feed(seg("u1", "I need gift cards", rev=4), 1.3)
    assert [e["type"] for e in dup] == ["status"] and dup[0]["warning"]
    assert d.feed(seg("u1", "I need gift cards", rev=5, final=False), 1.4) == []
    assert d.risk.score(1.2) == score


def test_final_at_same_revision_as_last_interim_is_accepted():
    d = confirmed()
    d.feed(seg("u1", "gift cards", rev=2, final=False), 1.0)
    d.feed(seg("u1", "gift cards", rev=2, final=True), 1.1)
    assert d.state()["score"] > 0.2


def test_cards_withheld_until_confirmed_then_fire():
    d = Detector(Config(), "s1")
    evs = run(d, SCAM)
    assert kinds(evs, "risk")[-1]["level"] == "high"
    assert kinds(evs, "intervention") == [] and kinds(evs, "alert") == []
    evs = d.set_elder(None, 10.0)
    assert [e["kind"] for e in kinds(evs, "intervention")] == ["codeword"]
    assert len(kinds(evs, "alert")) == 1


def test_silence_decays_through_tick():
    d = confirmed()
    run(d, SCAM)
    levels = [e["level"] for t in range(10, 900) for e in kinds(d.tick(float(t)), "risk")]
    assert levels and levels[-1] == "low"
    # score passed 0.95, so it escalated to hangup; the card stays latched as risk decays
    assert d.state()["intervention"] == "hangup"


def test_swap_rebuild_equals_fresh_detector():
    lines = [("0", "Hello?"), ("1", SCAM[0]), ("0", "Ryan? Are you okay?"), ("1", SCAM[1])]
    wrong = Detector(Config(), "s1")
    wrong.set_elder("1", 0.0)
    for i, (raw, text) in enumerate(lines):
        wrong.feed(seg(f"u{i}", text, "unknown", raw=raw, t=i * 3), i * 3 + 1.5)
    wrong.set_elder("0", 20.0)
    fresh = Detector(Config(), "s2")
    fresh.set_elder("0", 0.0)
    for i, (raw, text) in enumerate(lines):
        fresh.feed(seg(f"u{i}", text, "unknown", raw=raw, t=i * 3), i * 3 + 1.5)
    fresh.tick(20.0)
    a, b = wrong.state(), fresh.state()
    assert a["score"] == pytest.approx(b["score"]) and a["level"] == b["level"] == "high"


def test_risk_only_emitted_on_change():
    d = confirmed()
    run(d, SCAM)
    assert kinds(d.tick(4.6), "risk") == []


def test_seq_increases_and_clock_clamps():
    d = confirmed()
    evs = run(d, SCAM)
    seqs = [e["seq"] for e in evs]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
    later = d.feed(seg("u9", "gift cards"), 1.0)  # earlier clock than last call
    assert all(e["t"] >= evs[-1]["t"] for e in later)


def test_end_locks():
    d = confirmed()
    run(d, SCAM)
    d.end(30.0)
    with pytest.raises(RuntimeError):
        d.feed(seg("u9", "hi"), 31.0)
    with pytest.raises(RuntimeError):
        d.tick(31.0)


def test_timing_log_has_no_text():
    d = confirmed()
    run(d, SCAM)
    log = d.state()["timing"]
    assert log and all("text" not in row and "quote" not in row for row in log)
    assert log[0]["arrival_s"] - log[0]["end_s"] == pytest.approx(0.5)


def test_state_is_pure():
    d = confirmed()
    run(d, SCAM)
    before = d.state()
    d.state()
    assert d.state() == before
