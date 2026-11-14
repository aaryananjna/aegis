"""Free-tier AI limits (Groq: 8,000 tokens a minute): ask the AI at most once every
llm_min_interval_s. Lines in between aren't lost; the next request covers the last 60 s."""
from hangup_detect.config import Config
from hangup_detect.pipeline import Detector
from hangup_detect.types import make_segment


def feed(d, uid, text, t):
    d.feed(make_segment(uid, 0, "unknown", text, t, t + 1, True, speaker_raw=None), t + 1.5)


def test_requests_are_spaced_out():
    d = Detector(Config(), "s1")
    d.set_elder(None, 0.0)
    feed(d, "u0", "This is the fraud department at your bank.", 0.0)
    assert d.llm_request(1.5) is not None
    feed(d, "u1", "Buy gift cards right now.", 2.0)
    assert d.llm_request(3.5) is None          # too soon after the last request
    req = d.llm_request(1.5 + Config().llm_min_interval_s)
    assert req is not None and "u1" in [u for u, _ in req.utterances]  # nothing lost


def test_default_interval_keeps_under_groq_free_limit():
    # ~750 tokens a request: 60 / interval requests a minute must stay under 8,000 tokens.
    assert 60 / Config().llm_min_interval_s * 750 < 8000
