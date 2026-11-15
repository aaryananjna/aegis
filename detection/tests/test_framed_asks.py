"""A caller can't switch the rules off by putting "someone said" or "they said" in front of each
ask (security review, 2026-11-15). A retelling describes the past; "they said you need to move
your money" said TO the listener is still an ask. Real retellings and warnings stay calm."""
import pytest

from hangup_detect.replay import parse_call, replay


def levels(*lines):
    body = "".join(f"[{i * 5.0:.1f}-{i * 5.0 + 4.0:.1f}] {spk}: {t}\n" for i, (spk, t) in enumerate(lines))
    call = parse_call("# id: t\n# label: scam\n# source: synthetic\n# set: example\n" + body)
    out = []
    for ns in (True, False):
        evs = replay(call, no_speakers=ns, elder=None if ns else "spk0")
        out.append([e["level"] for e in evs if e["type"] == "risk"])
    return out


def test_framed_asks_from_a_fake_bank_still_warn():
    for lv in levels(
        ("spk1", "Hi, this is the fraud department at your bank."),
        ("spk1", "Someone said you need to move your money to a safe account right now."),
        ("spk1", "They said you have to buy gift cards and read me the numbers."),
    ):
        assert "high" in lv


@pytest.mark.parametrize("lines", [
    # The grandparent retelling a call she got.
    [("spk0", "A man called me yesterday. He said I had to buy gift cards right now."),
     ("spk1", "Mom, that was a scam. Did he say don't tell your family?"),
     ("spk0", "Yes, he said I should move my money to a safe account. I hung up.")],
    # A daughter warning ahead of time.
    [("spk1", "Mom, if someone says you need to move your money to a safe account, hang up."),
     ("spk1", "And if anyone says you have to buy gift cards, that's a scam."),
     ("spk0", "Okay honey, I'll hang up.")],
])
def test_retellings_and_warnings_stay_calm(lines):
    for lv in levels(*lines):
        assert "high" not in lv
