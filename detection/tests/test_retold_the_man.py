"""A victim retelling a scam to a real investigator ("The man said he was from the police")
is a report, not an impersonation (Codex blind set, 2026-11-15: a false Warning)."""
from hangup_detect.replay import parse_call, replay
from hangup_detect.rules import find_evidence
from hangup_detect.types import Tactic as T

CALL = """# id: t
# label: benign
# source: synthetic
# set: example
[0.0-4.3] spk1: Mrs. Durnell, I'm returning your message about the wire transfer you reported yesterday.
[4.6-8.9] spk0: The man said he was from the police. I feel such a fool.
[9.3-13.3] spk1: I'm sorry that happened. Your report is assigned to me, Investigator Kelby.
[13.8-16.5] spk0: Do you need me to move what's left?
[16.8-21.8] spk1: No. Speak to your bank about securing the account. We don't hold money for people.
"""


def test_the_man_said_is_a_retelling():
    assert T.IMPERSONATION not in {e.tactic for e in find_evidence("The man said he was from the police.", "u", 0.0)}


def test_real_investigator_follow_up_stays_calm():
    for ns in (True, False):
        evs = replay(parse_call(CALL), no_speakers=ns)
        assert "high" not in [e["level"] for e in evs if e["type"] == "risk"]


def test_a_caller_naming_himself_still_counts():
    assert T.IMPERSONATION in {e.tactic for e in find_evidence("This is officer Daniels from the police.", "u", 0.0)}
