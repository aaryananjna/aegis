"""Advice about what the real agency does ("The real IRS sends a letter, they never call and ask
for gift cards") is not an ask (real-caption test, 2026-11-15: a false Warning on a friend's
retelling). Outside a call about scams, an IRS caller asking for gift cards still counts."""
from hangup_detect.replay import parse_call, replay
from hangup_detect.rules import find_evidence
from hangup_detect.types import Tactic as T

FRIEND = """# id: t
# label: benign
# source: synthetic
# set: example
[0.0-0.6] spk0: Hello.
[1.2-4.3] spk1: Ruth, you will not believe the call I got this morning.
[4.9-5.6] spk0: What happened?
[6.2-10.1] spk1: A man said he was from the IRS and there was a warrant out for my arrest.
[10.7-12.4] spk0: Oh no, what did you do?
[13.0-17.5] spk1: He told me to buy gift cards and read him the numbers, I knew it was a scam.
[18.1-21.7] spk1: I said, I am calling my son, and I hung up on him.
[22.3-25.2] spk0: Good for you, they tried that on my sister last year.
[25.8-30.2] spk1: The real IRS sends a letter, they never call and ask for gift cards.
"""


def test_friend_retelling_with_advice_stays_calm():
    for ns in (True, False):
        lv = [e["level"] for e in replay(parse_call(FRIEND), no_speakers=ns) if e["type"] == "risk"]
        assert "high" not in lv


def test_an_irs_caller_asking_for_gift_cards_still_counts():
    tactics = {e.tactic for e in find_evidence("This is the IRS. You need to pay with gift cards today.", "u", 0.0)}
    assert {T.IMPERSONATION, T.PAYMENT} <= tactics
