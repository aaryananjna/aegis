"""Ask the AI sooner (Mihir's bank-reversal rehearsal, 2026-11-14): don't spend the first
request on "Hello?", and ask every 6 s instead of 8 (still under Groq's 8,000 tokens a minute)."""
from hangup_detect.config import Config
from hangup_detect.pipeline import Detector
from hangup_detect.types import make_segment


def det():
    d = Detector(Config(), "s1")
    d.set_elder(None, 0.0)
    return d


def feed(d, uid, text, t):
    d.feed(make_segment(uid, 0, "unknown", text, t - 1.0, t - 0.5, True), t)


def test_a_bare_greeting_does_not_use_up_a_request():
    d = det()
    feed(d, "u0", "Hello?", 1.0)
    assert d.llm_request(1.0) is None
    feed(d, "u1", "Hi, this is Mark from your bank's fraud department.", 4.0)
    assert d.llm_request(4.0) is not None   # asked now, not 8 s after "Hello?"


def test_one_real_line_is_enough():
    d = det()
    feed(d, "u0", "Grandma it's me, I'm in jail and I need bail money.", 2.0)
    assert d.llm_request(2.0) is not None


def test_asks_again_after_six_seconds():
    d = det()
    feed(d, "u0", "Hi, this is Mark from your bank's fraud department.", 2.0)
    assert d.llm_request(2.0) is not None
    feed(d, "u1", "Someone tried to take money from your account.", 7.0)
    assert d.llm_request(7.0) is None       # 5 s later: too soon
    assert d.llm_request(8.0) is not None   # 6 s later
