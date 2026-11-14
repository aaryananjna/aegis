"""Regression tests for the 2026-11-13 code review findings."""
from pathlib import Path

from hangup_detect.config import Config
from hangup_detect.pipeline import Detector
from hangup_detect.replay import parse_call, replay
from hangup_detect.rules import find_evidence
from hangup_detect.types import Tactic as T, make_segment

ROOT = Path(__file__).resolve().parents[1]


def tactics(text):
    return {e.tactic for e in find_evidence(text, "u", 0.0)}


# 1: numeric speaker ids from Deepgram must match the "0" from the elder tap
def test_numeric_speaker_raw_matches_string_elder():
    d = Detector(Config(), "s1")
    d.set_elder("0", 0.0)
    d.feed(make_segment("u1", 0, "unknown", "buy gift cards right now, don't tell anyone, it's me",
                        0, 1, True, speaker_raw=0), 1.0)
    assert d.state()["level"] == "low" and d.state()["intervention"] == "none"


# 2: inline comments in headers are stripped
def test_header_inline_comments_stripped():
    call = parse_call("# id: x\n# label: scam\n# source: team-staged\n"
                      "# group: irs-arrest            # same script idea\n"
                      "# onset_s: 4.0                 # when\n"
                      "# elder: 0                     # which spkN\n[0-1] spk0: hi\n")
    assert call.headers["group"] == "irs-arrest"
    assert call.headers["elder"] == "0" and call.onset_s == 4.0


# 3: scammers saying "this sounds like a scam" must not hide their own tactics
def test_preemptive_scam_denial_still_scores():
    assert T.PAYMENT in tactics("I know this sounds like a scam, but buy the gift cards right now")
    assert T.IMPERSONATION in tactics("This is a scam prevention call from Microsoft support")
    assert tactics("They said buy gift cards, that's a scam") == set()


# 5: "bail" the verb is not payment
def test_bail_verb_is_not_payment():
    assert T.PAYMENT not in tactics("Hi Grandma, it's me. I have to bail on dinner Sunday.")
    assert T.PAYMENT in tactics("I need you to post bail for me")
    assert T.PAYMENT in tactics("I need bail money tonight")


# 6: party mentioned before the secret doesn't make it a happy secret
def test_party_elsewhere_does_not_hide_secrecy():
    assert T.SECRECY in tactics("I got arrested at a party, please don't tell Mom")
    assert T.SECRECY not in tactics("We're planning a surprise party, so don't tell Mom, okay?")


# 7: curly apostrophes
def test_curly_apostrophes():
    text = "Please don’t tell Mom, it’s me"
    ev = find_evidence(text, "u", 0.0)
    assert {T.SECRECY, T.IMPERSONATION} <= {e.tactic for e in ev}
    for e in ev:
        assert text[e.span[0]:e.span[1]] == e.quote


# 8: replay uses the file's # elder: header by default, like eval does
def test_replay_uses_elder_header():
    text = (ROOT / "examples" / "scam-grandson.call").read_text().replace(
        "# set: example", "# set: example\n# elder: 0")
    text += "[25.0-27.0] spk0: Don't tell anyone? Gift cards right now? I'm calling your mother.\n"
    call = parse_call(text)
    assert replay(call, elder="0") != replay(call, no_speakers=True)
    assert replay(call) == replay(call, elder="0")


# 9: "It's me, Grandma" is the classic opener
def test_its_me_grandma():
    assert T.IMPERSONATION in tactics("It's me, Grandma, I'm in trouble")
    assert T.IMPERSONATION in tactics("It's me Nana")
    assert T.IMPERSONATION not in tactics("It's me, Ryan, how are you?")


# 10: tapping the elder keeps the meter's level when evidence doesn't change
def test_set_elder_keeps_hysteresis_level():
    d = Detector(Config(), "s1")
    for i, line in enumerate(["Nana it's me", "I need Google Play gift cards"]):
        d.feed(make_segment(f"u{i}", 0, "caller", line, i, i + 1, True), i + 1.0)
    assert d.risk.level == "high"
    t = 2.0
    while d.risk.score(t) >= 0.80:
        t += 1.0
    d.tick(t)
    assert d.risk.level == "high" and d.risk.score(t) >= 0.60
    evs = d.set_elder(None, t)
    assert d.risk.level == "high"
    assert all(e["level"] == "high" for e in evs if e["type"] == "risk")
