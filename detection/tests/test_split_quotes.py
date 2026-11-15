"""Since server #71 every sentence is its own caption. A retold quote or a warning split
into short sentences must stay calm; a scammer must still be caught when split the same way."""
import math

import pytest

from hangup_detect.config import Config
from hangup_detect.pipeline import Detector
from hangup_detect.types import make_segment

RETELL = ["Hello?", "Hi Joan, it's your sister.", "Oh Annie, I got one of those calls this morning.",
          "A young man said, Grandma, it's me.", "I'm in trouble.", "I need bail money.", "Please don't tell Mom.",
          "I asked him what we had for Thanksgiving and he hung up.", "Good for you."]
WARN = ["Hello?", "Hi Mom, I saw something on Facebook.", "There's a scam going around.",
        "People call pretending to be the bank.", "They tell you to buy gift cards.",
        "Don't tell your family, they say.", "So if anyone asks for gift cards, hang up and call me.", "Okay sweetheart."]
SCAM_NOT_A_SCAM = ["Hello?", "Grandma, it's me.", "Please don't hang up.", "I know this sounds like a scam but it's not.",
                   "I got arrested and they said I need bail money tonight.", "Arrested? Are you okay?",
                   "I'm okay but I need you to send two thousand dollars.", "Please don't tell Mom, she'll kill me."]
SCAM_USES_WARNING = ["Hello?", "This is Mark from the fraud department at your bank.", "There's a scam going around.",
                     "Your account was flagged.", "Go to the store and buy gift cards.",
                     "Read me the numbers on the back.", "Don't tell anyone at the branch."]
SCAM_SHORT = ["Hello?", "Hey grandma, it's me.", "I'm in kind of a mess.", "I need two thousand bucks wired tonight.",
              "Please don't tell mom."]


def peak(lines):
    d = Detector(Config(), "s1")
    d.set_elder(None, 0.0)
    levels = []
    for i, t in enumerate(lines):
        out = d.feed(make_segment(f"u{i}", 0, "unknown", t, i * 3.0, i * 3.0 + 2.5, True), i * 3.0 + 3)
        levels += [e["level"] for e in out if e["type"] == "risk"]
    end = len(lines) * 3
    for t in range(end, end + 20):
        levels += [e["level"] for e in d.tick(float(t)) if e["type"] == "risk"]
    return "high" if "high" in levels else "elevated" if "elevated" in levels else "low"


@pytest.mark.parametrize("lines", [RETELL, WARN], ids=["retell", "warning"])
def test_split_retelling_and_warning_stay_calm(lines):
    assert peak(lines) != "high"


@pytest.mark.parametrize("lines", [SCAM_NOT_A_SCAM, SCAM_USES_WARNING], ids=["not-a-scam", "uses-warning"])
def test_split_scams_are_still_caught(lines):
    assert peak(lines) == "high"


def test_short_split_scam_is_not_silenced():
    # On rules alone this one only ever reached "Be careful"; the AI layer takes it to a Warning.
    assert peak(SCAM_SHORT) in ("elevated", "high")
