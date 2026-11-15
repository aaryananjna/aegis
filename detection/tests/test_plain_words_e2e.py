"""Plain everyday wording from the end-to-end test (2026-11-15): calls a judge might improvise.

Before these rules only 2 of 10 improvised plain-worded scams reached a Warning on rules alone
("I'm calling from your bank", "send it back with Zelle", "pay a small fee", "the police will
come to your house", "read me that code"). Each new pattern alone stays Normal; the honest
look-alikes below must never warn. These calls were written for this test, so they are
practice calls, not held-out ones.
"""
import pytest

from hangup_detect.replay import parse_call, replay
from hangup_detect.rules import find_evidence
from hangup_detect.types import Tactic as T

SCAMS = {
    "grandkid-wreck": [
        "e:Hello?", "c:Grandpa? It's me. I messed up really bad.", "e:What happened?",
        "c:I was in a car wreck and the cops took me in. I'm at the station.",
        "c:I'm okay but I need three thousand dollars to get out tonight.",
        "c:Please don't say anything to Dad. Can you send it today?"],
    "bank-send-it-back": [
        "e:Hello?", "c:Hi, I'm calling from your bank about a problem with your account.",
        "c:We saw a strange charge for eight hundred dollars this morning.", "e:I didn't buy anything.",
        "c:To fix it you need to send that money back to us with Zelle."],
    "electric-shutoff": [
        "e:Hello?", "c:This is the electric company. Your bill is two months late.",
        "c:Your power will be turned off in thirty minutes.", "e:Thirty minutes?",
        "c:Go to the drugstore and get a prepaid card for four hundred dollars."],
    "won-ten-thousand": [
        "e:Hello?", "c:Congratulations! You won ten thousand dollars in our drawing.",
        "e:Well that's wonderful.", "c:Before we send it, you just pay a small fee of two hundred dollars."],
    "windows-errors": [
        "e:Hello?", "c:Hello, I'm calling from Windows about your computer.",
        "c:It has been sending us error messages all week.", "e:Oh dear.",
        "c:Your computer is sending us errors. Go to your computer and turn it on."],
    "back-taxes-police": [
        "e:Hello?", "c:I'm calling about the taxes you owe from last year.",
        "c:If you don't pay today, the police will come to your house.", "e:The police?",
        "c:Go to the store and buy gift cards. Then read me the numbers off the back."],
    "stuck-overseas": [
        "e:Hello?", "c:Honey, it's Robert. I'm stuck at the airport overseas.",
        "c:Somebody stole my wallet and my phone.",
        "c:Can you send me two thousand dollars through Western Union?",
        "c:Please don't tell your daughter, she doesn't like me."],
    "amazon-order-code": [
        "e:Hello?", "c:This is Amazon. Someone just ordered an iPhone on your account.",
        "e:That wasn't me!", "c:I can cancel it. I just sent a code to your phone.",
        "c:Read me that code so I can cancel the order."],
}

NORMAL = {
    "named-grandson-pizza": [
        "e:Hello?", "c:Hi Grandpa, it's Danny. Can you send me twenty dollars with Venmo for pizza?",
        "e:Of course.", "c:Thanks, I'll pay you back Friday."],
    "real-bank-stopped-it": [
        "e:Hello?", "c:Hi, I'm calling from your bank, First Valley. We saw a charge that didn't look like you, so we stopped it.",
        "c:You don't need to do anything. A new card is in the mail."],
    "planned-outage": [
        "e:Hello?", "c:This is City Light and Power. We are replacing a pole on your street.",
        "c:The power will be shut off Tuesday from nine to noon.", "c:It comes back on by itself."],
    "utility-late-fee": [
        "e:Hello?", "c:This is Valley Electric billing. Your last payment came in after the due date.",
        "c:So there is a late fee of five dollars on your next bill. You can pay it whenever the bill comes."],
    "friend-police-report": [
        "e:Hello?", "c:Margie, it's Ruth. Somebody broke into my car last night.",
        "c:The police will come by tomorrow to take a report.", "e:Oh no. Are you okay?"],
    "library-raffle": [
        "e:Hello?", "c:Hi, this is Joan at the library. You won the raffle basket!",
        "c:There's no fee, just come pick it up before we close at five."],
    "daughter-delayed-flight": [
        "e:Hello?", "c:Hi Mom, it's Linda. I'm stuck at the airport, my flight is delayed.",
        "c:I'll call you when I land. Don't wait up."],
    "son-helps-with-email": [
        "e:Hello?", "c:Hi Dad, it's Tom. Go to your computer and open the email I sent you.",
        "c:The photos of the kids are in there."],
    "elder-plans-water-heater": [
        "e:Hello?", "c:Hi Mom, it's Linda. Did the plumber call back?",
        "e:Yes. I need two thousand dollars for the new water heater, so I'll write him a check.",
        "c:That sounds right. I'll come by Saturday."],
}


def run(lines, no_speakers):
    body, t = ["# id: t", "# label: scam", "# source: synthetic"], 0.0
    for line in lines:
        who, text = line.split(":", 1)
        body.append(f"[{t:.1f}-{t + 3.0:.1f}] {'spk0' if who == 'e' else 'spk1'}: {text}")
        t += 3.6
    evs = replay(parse_call("\n".join(body)), elder="0", no_speakers=no_speakers)
    return ([e["level"] for e in evs if e["type"] == "risk"],
            [e for e in evs if e["type"] in ("intervention", "alert")])


@pytest.mark.parametrize("no_speakers", [False, True])
@pytest.mark.parametrize("name", SCAMS)
def test_plain_worded_scams_reach_a_warning(name, no_speakers):
    levels, cards = run(SCAMS[name], no_speakers)
    assert "high" in levels and cards


@pytest.mark.parametrize("no_speakers", [False, True])
@pytest.mark.parametrize("name", NORMAL)
def test_honest_look_alikes_never_warn(name, no_speakers):
    levels, cards = run(NORMAL[name], no_speakers)
    assert "high" not in levels and not cards


@pytest.mark.parametrize("text,tactic", [
    ("I'm calling from your bank about your account.", T.IMPERSONATION),
    ("You need to send that money back to us with Zelle.", T.PAYMENT),
    ("Before we send it, you just pay a small fee.", T.PAYMENT),
    ("I need three thousand dollars to get out tonight.", T.PAYMENT),
    ("The police will come to your house.", T.THREAT),
    ("Your power will be turned off in thirty minutes.", T.THREAT),
    ("Your computer has been sending us error messages.", T.THREAT),
    ("I just sent a code to your phone.", T.REMOTE_ACCESS),
    ("Read me that code so I can cancel the order.", T.REMOTE_ACCESS),
    ("Somebody stole my wallet.", T.DISTRESS),
])
def test_each_plain_phrase_is_flagged(text, tactic):
    assert tactic in {e.tactic for e in find_evidence(text, "u", 0.0)}


@pytest.mark.parametrize("text", [
    "The power will be off from nine to noon on Tuesday.",
    "The power will be shut off Tuesday morning for repairs.",
    "There is a late fee of five dollars on your next bill.",
    "There's no fee, just come pick it up.",
    "This is Dana from First Valley Bank.",
    "I need a thousand more steps today to hit my goal, ha.",
    "My flight is delayed so I'm stuck here a while.",
    "I'm going to send you the money for the tickets with Zelle.",  # paying the listener, not an ask
    "I'll pay you back on Venmo tonight.",
])
def test_everyday_lines_are_not_flagged(text):
    hits = find_evidence(text, "u", 0.0)
    assert not [e for e in hits if e.tactic is not T.URGENCY], hits
