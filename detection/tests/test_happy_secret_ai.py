"""A real Deepgram call (recorded-01): a nephew keeps a surprise party secret and collects $20.
Rules stay calm, but the AI flagged the secrecy twice plus the $20, and two AI tricks raised a
Warning by themselves. Secrecy about a birthday or surprise is normal, for the AI too."""
import json
from pathlib import Path

from hangup_detect.config import Config
from hangup_detect.pipeline import Detector
from hangup_detect.replay import parse_call
from hangup_detect.types import make_segment

CALL = Path(__file__).resolve().parents[1] / "eval" / "calls" / "recorded" / "recorded-01-surprise-party-collection.call"


def ai(*hits):
    return json.dumps({"tactics": [{"tactic": t, "utterance_id": u, "quote": q} for t, u, q in hits]})


def run(segs, answers):
    """Feed lines labels-off; after the given line index, apply the AI answer for a fresh request."""
    d = Detector(Config(), "s1")
    d.set_elder(None, 0.0)
    levels, cards = [], []
    for i, s in enumerate(segs):
        t = s.end_s + 0.5
        evs = d.feed(s, t)
        if i in answers:
            req = d.llm_request(t)
            assert req is not None
            evs += d.apply_llm(req.seq, answers[i], t + 0.6)
        levels += [e["level"] for e in evs if e["type"] == "risk"]
        cards += [e for e in evs if e["type"] == "intervention"]
    return levels, cards


def segs_of(call):
    return [make_segment(s.utterance_id, 0, "unknown", s.text, s.start_s, s.end_s, True) for s in call.lines]


def test_surprise_party_call_stays_calm_with_the_ai_answers_groq_gave():
    segs = segs_of(parse_call(CALL.read_text()))
    # The exact answers Groq returned for this call (2026-11-14 20:05), at the same points.
    answers = {
        3: ai(("secrecy", "u2", "Make sure uncle Frank can't hear me.")),
        6: ai(("secrecy", "u2", "Make sure uncle Frank can't hear me."),
              ("secrecy", "u5", "keep this at total secret")),
        10: ai(("secrecy", "u2", "Make sure uncle Frank can't hear me."),
               ("secrecy", "u5", "keep this at total secret"),
               ("payment", "u9", "collecting $20 per person for the gig")),
    }
    levels, cards = run(segs, answers)
    assert "high" not in levels and not cards


def test_ai_secrecy_still_counts_without_a_happy_occasion():
    lines = ["Grandma it's me, I'm in some trouble.",
             "Make sure nobody else can hear this, keep it a total secret.",
             "I need you to send two thousand dollars by wire tonight."]
    segs = [make_segment(f"u{i}", 0, "unknown", t, i * 4.0, i * 4.0 + 3, True) for i, t in enumerate(lines)]
    answers = {2: ai(("secrecy", "u1", "keep it a total secret"), ("payment", "u2", "send two thousand dollars by wire"))}
    levels, _ = run(segs, answers)
    assert "high" in levels
