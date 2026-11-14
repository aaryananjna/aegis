"""Phrases from FTC, FBI IC3, IRS, AARP and bank fraud pages (2026-11-13 research).

Each positive is a caller line built from a published scam script beat. Negatives are
normal calls that share words with them.
"""
import pytest

from hangup_detect.rules import find_evidence
from hangup_detect.types import Tactic as T

POS = [
    # FTC gift card page: "give them the numbers off the back of the card"
    (T.PAYMENT, "Give me the numbers off the back of the card"),
    # FTC Aug 2025 spotlight: "keep your money safe", move it to protect it
    (T.PAYMENT, "We need to move your money to a safe account to protect it"),
    (T.PAYMENT, "Transfer your savings so we can keep your money safe"),
    # FTC tech support page: "federal safety locker"
    (T.PAYMENT, "Put the cash in a federal safety locker"),
    # FTC / IC3: gold, couriers, QR code ATM deposits
    (T.PAYMENT, "Withdraw the cash and buy gold bars"),
    (T.PAYMENT, "Scan this QR code at the bitcoin machine"),
    # FTC phone scams page: prize then fee
    (T.PAYMENT, "You just need to pay the taxes and fees first to claim your prize"),
    # FTC tech support refund scam: "refunded you too much money"
    (T.PAYMENT, "We accidentally refunded you too much money, send the difference back"),
    # FTC gov impersonation: "you've won a federally supervised lottery"
    (T.IMPERSONATION, "Congratulations, you've won a federally supervised lottery"),
    (T.IMPERSONATION, "I'm an agent with the Federal Trade Commission, my badge number is 4471"),
    # IRS page: "a warrant will be issued for their arrest"
    (T.THREAT, "If you don't call back a warrant will be issued for your arrest"),
    # FTC spotlight: SSN "linked to a crime like drug smuggling, money laundering"
    (T.THREAT, "Your Social Security number is linked to money laundering"),
    (T.THREAT, "Someone is using your account right now"),
    # FTC 2026 report / Chase: coaching the victim to lie to the bank
    (T.SECRECY, "If the teller asks, tell them it's for home renovations"),
    (T.SECRECY, "Don't talk to your family about this"),
    # Bank 'never' lists: asking for a code or credentials
    (T.REMOTE_ACCESS, "Read me the verification code we just texted you"),
    # FTC tech support page: "your money is at risk"
    (T.URGENCY, "Your money is at risk and you have to protect it immediately"),
    # AARP grandparent: "a pregnant woman was injured"
    (T.DISTRESS, "I hit a car and a pregnant woman was injured"),
]

NEG = [
    (T.PAYMENT, "The recipe is on the back of the card I gave you"),
    (T.PAYMENT, "I keep my money safe in the credit union"),
    (T.PAYMENT, "Grandpa used to collect gold coins"),
    (T.PAYMENT, "Did you pay the property taxes yet?"),
    (T.IMPERSONATION, "You won the church raffle, Margaret!"),
    (T.THREAT, "The movie was about money laundering"),
    (T.THREAT, "Is someone using your old laptop?"),
    (T.SECRECY, "Tell the teller I said hi"),
    (T.REMOTE_ACCESS, "The code for the garage door is 1234"),
    (T.URGENCY, "Is your money in the joint account?"),
]


def tactics(text):
    return {e.tactic for e in find_evidence(text, "u", 0.0)}


@pytest.mark.parametrize("tactic,text", POS)
def test_research_positive(tactic, text):
    assert tactic in tactics(text)


@pytest.mark.parametrize("tactic,text", NEG)
def test_research_negative(tactic, text):
    assert tactic not in tactics(text)


def test_prize_and_fee_together_reach_high():
    from hangup_detect.config import Config
    from hangup_detect.risk import RiskModel
    m = RiskModel(Config())
    for e in find_evidence("Congratulations, you've won a federally supervised lottery. "
                           "You just need to pay the taxes and fees first to claim your prize.",
                           "u", 0.0):
        m.add(e)
    assert m.update_level(0.0) == "high"
