"""Layer 1: fast deterministic patterns for the 8 scam tactics.

Each hit keeps the exact matched words (quote + span into the original text)
so the elder screen can highlight them.

Known gaps (documented, not handled here):
- A tactic split across two utterances ("go buy some..." / "...gift cards").
  The LLM layer's 60 s window covers it.
- Sarcasm, and negation further than two words before the match.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .types import Evidence, Tactic as T

_I = re.IGNORECASE

PATTERNS: dict[T, list[str]] = {
    T.IMPERSONATION: [
        # "it's me" with no name right after it (real family say their name)
        r"\bit'?s me\b(?!,?\s+(?!(?:grandma|grandpa|nana|papa|granny|gran|mom|mum|dad|grandmother|grandfather|aunt|auntie|uncle)\b)(?-i:[A-Z][a-z]+)\b)",
        r"\b(this is )?your (favorite )?(grandson|granddaughter|grandkid|nephew|niece)\b",
        r"\b(this is|i'?m) (officer|detective|sergeant|deputy|agent)\b",
        r"\b(calling )?(from|with) the (police|sheriff'?s? (office|department)|court|irs)\b",
        r"\b(irs|internal revenue service|social security administration)\b",
        r"\b(calling from|this is) (medicare|social security)\b",
        r"\b(microsoft|apple|amazon|windows|geek squad|norton|mcafee) (support|security|technical|tech|fraud|billing)\b",
        r"\b((your|the) )?bank'?s? (fraud|security) (department|team|division|line|desk|center|office)\b",
        r"\b(public defender|your (grandson'?s|lawyer|attorney))\b",
        # FTC: prize and lottery callers, fake FTC/FBI agents with badge numbers
        r"\byou('ve| have)? (just )?won\b(?=.{0,40}(\$\s?\d|\b\d[\d,]* (dollars|bucks)\b|\b(lottery|sweepstakes|prize|million|"
        r"thousand|grant|cash|car|vacation)\b))",
        # A stranger's money lure (demo test, 2026-11-15): big free money or a grant, before any ask.
        # The lure alone stays Normal; it makes the fee or bank number that follows a Warning.
        r"\bgive you\b.{0,30}(\$\s?\d{1,3}(,\d{3})+|\b\d{1,3}(,\d{3})+|\b\d{4,}|\b(thousand|million)\b)"
        r".{0,40}\b(for free|for no reason|no strings attached|free of charge|nothing in return)\b",
        r"\byou('ve| have)? (qualify|qualified|are eligible|'?re eligible|been selected|been approved) (for|to (receive|get)) "
        r"(a |an )?(free |federal |government )?(grant|prize|reward|cash award|award)\b",
        # A utility company as the caller: "This is Valley Electric Dispatch", "calling from the gas company"
        r"\b(this is|calling (from|on behalf of)|i'?m (calling )?(with|from)|we'?re (calling )?(with|from)) (the |your )?"
        r"([a-z]+ ){0,3}(electric|electricity|power|energy|gas|water|utility|utilities)"
        r"(?= (company|co|dispatch|department|services?|billing|utility|authority|and light|and electric)\b|\s*[.,!]|$)",
        r"\b(federally supervised lottery|publishers clearing house)\b",
        r"\b(agent|investigator|officer) (with|from) the (federal trade commission|ftc|fbi)\b",
        r"\bbadge number\b",
        r"\b(bank|card|account)('?s)? (fraud|security) (prevention|protection|unit|center|centre)\b",
        # Plain wording (classic asks, 2026-11-14): a brand or bank named as the caller
        r"\b(this is|i'?m (with|from)|calling (from|on behalf of)|i work (for|at)) (the )?(microsoft|apple|amazon|windows|geek squad|norton|mcafee|paypal|chase|wells fargo|bank of america|citi(bank)?|capital one)\b",
        r"\b(technician|tech|agent|specialist|representative|rep) (with|from|at) (microsoft|apple|amazon|windows|geek squad|norton|mcafee|paypal|chase|wells fargo|bank of america|citi(bank)?|capital one)\b",
        r"\b(grand )?prize winner\b",
        r"\b(fraud|security|card services) (desk|team|department|line|unit|center|centre|office) (at|of|from|with|for) "
        r"(the |your )?(\w+ ){0,3}(bank|credit union|savings|federal)\b",
        # Plain wording (end-to-end test, 2026-11-15): "I'm calling from your bank". A real bank
        # names itself ("this is Dana from First Valley Bank"); alone this stays Normal.
        r"\bcalling (you )?from (your|the) (bank|credit union|credit card company|card company)\b",
    ],
    T.URGENCY: [
        r"\b(right now|right away|immediately|as soon as possible|asap|before it'?s too late)\b",
        r"\b(no time|hurry|within the hour|in the next (hour|\d+ minutes)|emergency)\b",
        r"\burgent(ly)?\b(?! care)",
        r"\byour (money|savings|account|accounts) (is|are) at risk\b",  # FTC tech support
    ],
    T.SECRECY: [
        r"\b(please )?(don'?t|do not|you can'?t|you cannot) (tell|call|say anything to|mention (this|it) to) "
        r"(mom|dad|anyone|anybody|my (mom|dad|parents)|your (son|daughter|family|bank|kids))\b",
        r"\bkeep (this|it) (between us|a secret|quiet)\b",
        r"\bthis (stays|is) between us\b",
        r"\b(gag order|don'?t let the bank know)\b",
        # FTC 2026 / Chase: coaching the victim to lie to the bank, cutting off family
        r"\b(if|when) the (teller|bank) asks\b",
        r"\btell (the teller|the bank|them) (it'?s|that it'?s) for\b",
        r"\blie to (the )?(bank|teller)\b",
        r"\bdon'?t (talk|speak) to (your )?(family|friends|kids|anyone)\b",
        r"\b(don'?t|do not)( you dare)? (call|contact|tell|go to) (the )?(police|cops|bank|authorities|sheriff)\b",
    ],
    T.PAYMENT: [
        r"\b((itunes|google play|apple|steam|target|walmart|amazon|visa|ebay) )?gift ?cards?\b",
        r"\b(numbers?|codes?) (on|off|from) the back\b",
        # FTC Aug 2025: "move your money to keep it safe", safe accounts, safety lockers
        r"\b(move|transfer|put) (your|the) (money|savings|funds|cash)\b.{0,40}\b(safe|protect|secure)",
        r"\b(safe|secure|protected) account\b",
        r"\bkeep your money safe\b",
        r"\bfederal safety locker\b",
        # FTC / IC3: gold, QR code ATM deposits, prize fees, refund overpayment
        r"\b(buy|purchase) (gold|silver)\b|\b(gold|silver) bars?\b",
        r"\bqr code\b",
        r"\bpay (the |a |any )?(taxes|fees?|shipping|processing|registration)\b.{0,40}\b(claim|receive|release|get) (your|the) (prize|winnings|money|reward)",
        r"\b(refunded|overpaid|refund) you too much\b|\bsend (back )?the difference\b",
        r"\b(bit ?coin( atm| machine)?|crypto(currency)?)\b",
        r"\b(wire (the )?(money|transfer)|wire it|western union|moneygram)\b",
        r"\b(zelle|venmo|cash ?app) (it|the money|me)\b",
        r"\b(courier|driver|someone) (will|to|can) (come )?(pick up|collect)\b",
        # Everyday wording of the same payment tricks (trick families, 2026-11-14)
        r"\b(green ?dot|reload(able)? (pack|card)|prepaid (debit )?card|vanilla (card|visa)|money ?pak)\b",
        r"\bread me the (receipt|card|pin|serial) number\b",
        r"\b(read|give|tell|text|send) (me|us)( off)? (the |those |all the )?(numbers?|codes?|claim codes?|pin)"
        r"( on| from| off)? (the |that |your )?(receipts?|cards?|back)\b",
        r"\b(take|snap|send) (me )?(a )?(picture|photo|pic) of (the )?(back of )?(the )?(cards?|receipts?)\b",
        # The grandparent about to hand over a card (demo test, 2026-11-15). Labels off, every line
        # is scored; on its own it stays Normal (a pizza order), with a threat or a lure it warns.
        r"\blet me (give|read|get|grab|find) (you )?(my |the )?(credit card|debit card|card|bank account|account)( number| numbers)?\b",
        r"\bmy (credit card|debit card|card|account) number is\b",
        r"\b(send|mail|overnight|bring) (us |me )?(a |the )?(cashier'?s check|money order)\b",
        r"\b(send|transfer|move) .{0,30}\bto (our|a|the) (secure|safe|cancellation|reversal|holding|protected) (account|code|wallet)\b",
        r"\breversal transfer\b",
        r"\b(need|want|pay|bring|give) .{0,25}\bcash (up ?front|today|right now|before|in advance)\b",
        r"\b(need|pay|send|requires?|have to pay) .{0,40}\b(withholding|processing|release|insurance|transfer|customs) (fee|tax|stamp)",
        r"\b(post|pay) (a |the )?(compliance |cash |surety )?bond\b",
        r"\b(bail money|bail bond|(pay|post|make) (my |the |his |her )?bail|bail is set)\b",
        # Asking for card, bank or identity numbers (bank "we'll never ask" lists)
        r"(?#exact)\b(give|read|tell|verify|confirm|need|provide|share|say|what'?s|what is)\b.{0,30}\b(your|the) (full |long |whole |16[- ]digit )?"
        r"(credit card|debit card|card|visa|mastercard|amex|bank account|checking account|savings account|account|routing|social security|medicare|atm) (number|numbers|digits)\b",
        r"\b(give|read|tell|verify|confirm|need|provide|share|say|what'?s|what is|do you have|have you got|grab)\b.{0,60}\b(social security number|ssn|pin( number)?|passcode|password|security code|cvv|expiration date)\b",
        r"\b(give|read|tell|verify|confirm|need|provide|share|what'?s|what is)\b.{0,30}\bnumbers? on (your|the) (visa|card|credit card|debit card|mastercard|amex)\b",
        r"\b(three|3|four|4) digits on the back\b",
        r"\b(money|pay|cash|paying) for (a|an|the|my) (lawyer|attorney)\b",
        # Bank "reversal" scam: you have to undo the fraud yourself by sending money
        r"\b(reverse|reversal|cancell?ation) (the )?(transfer|transaction|wire|payment)\b.{0,25}\byourself\b"
        r"|\b(do|initiate|make|send|start) (a |the )?(reverse|reversal) (transfer|transaction|wire|payment)\b",
        r"\b(send|pay|wire|bring|transfer)\b.{0,40}\b(dollars|bucks|grand)\b.{0,15}\bor (you'?ll|you will|else|she'?ll|he'?ll|they'?ll)\b",
        r"\b(taxes|fees?) first\b|\bbefore (we|i) (can )?(deliver|release|send|ship|mail) (the |your )?(check|prize|money|winnings)\b",
        # Plain wording (end-to-end test, 2026-11-15). Each one alone stays Normal; it takes a
        # second trick (a claim to be someone, a threat, secrecy) to warn.
        # "send that money back to us with Zelle", "send me two thousand through Western Union"
        r"\b(send|pay|transfer|move|wire)\b.{0,40}\b(with|through|by|using|via|on|over) (zelle|venmo|cash ?app|paypal|western union|moneygram)\b",
        # A fee before the money comes: "before we send it, you just pay a small fee"
        r"\bbefore (we|i) (can )?(deliver|release|send|ship|mail) (it|them)\b.{0,30}\bpay\b",
        r"\bpay (us |me )?(a|the|one) (small|little|tiny|one[- ]time|up ?front|advance|refundable|processing|handling|release) fee\b",
        # A stranger's ask for thousands: "I need three thousand dollars", "can you send me two grand"
        r"\b(i need|send me|wire me|lend me|loan me|can you send( me)?)\b.{0,20}\b(thousand (dollars|bucks)|grand)\b",
    ],
    T.THREAT: [
        r"\bwarrant (is )?out (for|on) (you|your)\b",
        r"\b(cuff|arrest|detain|handcuff) you\b",
        r"(?#exact)\b(shut(ting)?|cut(ting)?) off your (power|electricity|service|water|gas)( meter)?\b",
        r"\bdisconnection (order|notice)\b",
        r"\b(warrant (out )?for (your|his|her) arrest|arrest warrant)\b",
        r"\b(you|you'll|you will) (be|get) arrested\b",
        r"\b(go|going|sent|put you) (to|in) (jail|prison)\b",
        r"\b(i|i'?ve|he|she) (got|been|was) arrested\b",
        r"\b(legal action against you|sue you|deport(ed|ation)?)\b",
        r"(?#exact)\b(shut (off|down)|disconnect) your (power|electricity|service|water|gas)\b",  # "shut off water" is a plumber
        r"\b(suspend|freeze|close) your (account|benefits|social security|license)\b",
        # IRS page and FTC spotlight wording
        r"\bwarrant (will be|has been|is being) issued\b",
        r"\b(linked|connected|tied) to (a crime|money laundering|drug (smuggling|trafficking)|fraud)\b",
        r"\bsomeone is (using|trying to (use|access|empty)) your (account|card|bank account|credit card)\b",
        r"\b(account|benefits|coverage|card) (will|is going to) be (frozen|suspended|cancell?ed|closed)\b",
        r"\blose (your )?(coverage|benefits|account)\b",
        r"\b(computer|laptop|pc|phone|device) (is|has been|got|was) (infected|hacked|compromised)\b|\b(computer|laptop|pc) has (a )?virus\b"
        r"|\b(it'?s|you'?re|you are) infected\b",
        r"\b(we('ve)?|i('ve)?) (got|have) your (daughter|son|grandson|granddaughter|husband|wife|kid|child|grandkid)\b",
        r"\b(never see (her|him|them) again|if you want (her|him|them) back)\b",
        # The fake fraud alert: "someone just tried to take $900 from your checking account"
        r"\b(someone|somebody|a (man|woman|person)|a scammer|hackers?)\b.{0,30}\b(tried|attempted|is trying|was trying) to "
        r"(send|take|withdraw|transfer|move|wire|charge|use|access|empty|steal)\b.{0,50}\b(your|the) "
        r"(checking|savings|account|bank account|card|debit card|credit card|funds|money)\b",
        # Plain wording (end-to-end test, 2026-11-15)
        # "the police will come to your house", "the police arrested me"
        r"\b(police|sheriff|cops|officers|marshals|deputies) (will|are going to|are gonna) (come|be (sent|coming)|show up|arrest|pick you up)\b",
        r"\b(police|cops|they) (have |just )?arrested (me|him|her)\b",
        # A shutoff with a deadline: "your power will be turned off in thirty minutes". A planned
        # outage ("the power will be off Tuesday from nine to noon") has no countdown.
        r"\b(power|electricity|service|water|gas|lights) (will|is going to|are going to) (be|get) (turned|shut|cut|switched) off\b"
        r".{0,20}\b((in|within) (the next )?(\w+ ){1,2}(minutes?|hours?)|today|tonight)\b",
        # Tech support opener: "your computer has been sending us error messages"
        r"\b(computer|laptop|pc|device) (is|has been|keeps) sending (us |out )?(\w+ )?(errors?|messages|alerts|warnings|signals)\b",
    ],
    T.VERIFICATION_AVOIDANCE: [
        r"\bno time (for|to) (that|explain|questions)\b",
        r"\bthere'?s no time\b",
        r"\b(don'?t ask (me )?(questions|why)|stop asking|just trust me|why are you asking)\b",
        r"\b(i can'?t explain|(that )?doesn'?t matter)\b",
        r"\byou don'?t need to (call|check|verify)\b",
        r"\b(stay on the (line|phone)|do not hang up|don'?t hang up)\b",
    ],
    T.REMOTE_ACCESS: [
        r"\bremote (connection|login|session code)\b|\bremote control (of|over) your (computer|screen|phone)\b",
        r"\b(read|give|tell) (me|us)( off)? the (letters and )?numbers (on|from|off) your \w+ card\b",
        r"\bsit down at your computer\b",
        r"\b(anydesk|teamviewer|ultraviewer|logmein|supremo)\b",
        r"\bremote (access|desktop|support|session)\b",
        r"\b(take control of|get into|connect to) your (computer|phone|screen)\b",
        r"\bshare your screen\b",
        r"\bpress (the )?windows (key|and r)\b",
        # Bank "never" lists: asking for a code or credentials
        r"\b(read|give|tell) me (the|your) (verification |security |one[- ]time )?(code|pin|password)\b",
        r"\b(install|download) (the |this |an? |my )?(app|program|software|tool)\b.{0,30}\bso (i|we) can (fix|clean|remove|access|see|get into|connect|scan)\b",
        r"\bread (that|the|this|your) .{0,20}\bcode\b.{0,15}\b(back|to me|to us)\b",
        r"\b(texted|sent|text|send) you (a|an) (\w+ ){0,3}code\b",
        # Plain wording (end-to-end test, 2026-11-15): "I just sent a code to your phone",
        # "read me that code", "go to your computer and turn it on"
        r"\b(texted|sent) (a|an) (\w+ ){0,3}code to your (phone|cell|cell phone|email|number)\b",
        r"\b(read|give|tell|send) me (that|this) (verification |security |one[- ]time )?(code|pin|password)\b",
        r"\b(go|get) (over )?to your computer\b",
    ],
    T.DISTRESS: [
        r"\bi'?m (so )?(scared|terrified|in trouble|in big trouble|hurt|bleeding|crying)\b",
        r"\bi (got|was) in (an|a car) accident\b",
        r"(?#exact)\b(please help( me)?|i need your help)\b",  # "i need help" is everyday talk
        r"\b(i'?m|he'?s|she'?s) in the hospital\b",
        r"\bbroke my (nose|arm|leg|wrist)\b",
        r"\bpregnant woman\b",  # AARP grandparent scam
        # Stranded traveler (end-to-end test, 2026-11-15): "somebody stole my wallet", "I'm stuck at the airport"
        r"\b(stole|took) my (wallet|purse|passport)\b|\bmy (wallet|purse|passport) (was|got) stolen\b",
        r"\bi'?m (stuck|stranded) (at|in) (the|a)\b",
    ],
}

# Captions drop small words ("stay on line"). Each small word written in a pattern, alone or as
# a group of only small words ("(your|the) "), becomes optional. Pronouns that carry meaning
# (i, you, we, me, it, this) stay required. A small word only becomes optional after a real
# word, so "from the police" can't shrink to just "police".
_SMALL = "the|a|an|to|on|in|of|for|at|your|my|our|his|her|their|with|from"
_SMALL_WORD = re.compile(rf"(?:(?<=\\b)|(?<=[ (|]))({_SMALL}) ")
_SMALL_GROUP = re.compile(rf"\(((?:{_SMALL})(?:\|(?:{_SMALL}))*)\) ")


def _required_path(prefix: str) -> str:
    """Words a match must already have passed to reach the end of `prefix`.

    Drops sibling alternatives ("a|b"), optional groups ("(...)?") and lookarounds.
    """
    stack: list[list[str]] = [[]]
    i = 0
    while i < len(prefix):
        ch = prefix[i]
        if ch == "\\":
            if prefix[i + 1:i + 2] != "b":
                stack[-1].append(prefix[i:i + 2])
            i += 2
            continue
        if ch == "(":
            if prefix[i + 1:i + 2] == "?" and prefix[i + 2:i + 3] in ("!", "=", "<"):
                depth = 0  # skip the whole lookaround
                while i < len(prefix):
                    depth += {"(": 1, ")": -1}.get(prefix[i], 0) if prefix[i - 1:i] != "\\" else 0
                    i += 1
                    if depth == 0:
                        break
                continue
            stack.append([])
            i = prefix.index(":", i) + 1 if prefix[i + 1:i + 2] == "?" else i + 1
            continue
        if ch == "|":
            stack[-1] = []
        elif ch == ")":
            inner = stack.pop()
            if prefix[i + 1:i + 2] in ("?", "*"):
                i += 1  # optional: a match can skip it
            else:
                stack[-1] += inner
        else:
            stack[-1].append(ch)
        i += 1
    return "".join(part for level in stack for part in level)


def _loosen(pattern: str) -> str:
    if pattern.startswith("(?#exact)"):  # opted out: the small word is what makes it a tactic
        return pattern
    def repl(m: re.Match, wrap: str) -> str:
        before = _required_path(pattern[:m.start()])
        return wrap.format(m.group(1)) if re.search(r"[a-z]", before) else m.group(0)
    pattern = _SMALL_GROUP.sub(lambda m: repl(m, "(?:(?:{}) )?"), pattern)
    return _SMALL_WORD.sub(lambda m: repl(m, "(?:{} )?"), pattern)


COMPILED = {t: [re.compile(_loosen(p), _I) for p in ps] for t, ps in PATTERNS.items()}

# Which impersonation patterns claim to be family (the first two); the rest claim to be an
# official or a company. Family callers get the code word card; others get "call back".
_FAMILY_PATTERNS = 2

_APOSTROPHES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'"})

# Skip a single match when "not/never/no" sits within two words before it.
_NEGATED = re.compile(r"\b(not|never|no)\s+(?!(a )?(worry|worried|panic|joke|joking|kidding|lying|problem|rush|drill)\b)(\w+\s+){0,2}$", _I)
# Skip the whole utterance when it describes a scam rather than runs one.
# Narrow on purpose: scammers say "I know this sounds like a scam" to get ahead of doubt.
_DESCRIBES_SCAM = re.compile(r"\b(that'?s|it'?s) a scam\b|\bscammers? (said|told|asked)\b", _I)
# Secrecy about a happy surprise is normal family talk: the event is named after the secret
# ("don't tell Mom about the party") or the call says outright it's a surprise.
_HAPPY_AFTER = re.compile(r"^[^.!?]*\b(surprise|party|birthday)\b", _I)
_HAPPY_ANY = re.compile(r"\b(it'?s a surprise|surprise (party|dinner|visit|trip)|birthday (party|surprise))\b", _I)


# Speech fillers that captions can drop into the middle of a phrase ("gift, um, cards").
# Only pure fillers: "like" and "so" carry meaning and stay.
_FILLER = re.compile(r"[,\s]*\b(?:um+|uh+|erm+|hmm+|ah+|mm+)\b[,]?\s*", re.IGNORECASE)


def _strip_fillers(text: str) -> tuple[str, list[int]]:
    """Text without fillers, plus pos[i] = index in the original text of clean char i."""
    clean: list[str] = []
    pos: list[int] = []
    last = 0
    for m in _FILLER.finditer(text):
        clean.append(text[last:m.start()])
        pos.extend(range(last, m.start()))
        clean.append(" ")  # keep word boundaries
        pos.append(m.start())
        last = m.end()
    clean.append(text[last:])
    pos.extend(range(last, len(text)))
    return "".join(clean), pos


# ---- Talking ABOUT scams -------------------------------------------------------------------
# People warn each other ("if anyone calls and says gift cards, hang up") and retell calls they
# beat ("a man said he was from the IRS"). Those words are reported speech, not an ask.
# A match is skipped when a reporting frame comes before it in the same sentence. A direct ask
# to the listener ("you need to buy gift cards") is never inside such a frame, so it still counts.

_WHO = (r"(someone|somebody|anyone|anybody|people|scammers?|crooks?|con (men|artists?)"
        r"|(this|that|a|some) (young |nice |strange |old )?(man|guy|woman|lady|girl|boy|fellow|kid))")
# Always a frame: a stranger's words retold, a hypothetical caller, or "pretending to be".
_STRONG_FRAME = re.compile(
    rf"\b{_WHO}\s+((\w+\s+){{0,2}}?)(said|says|say|told|tells|tell|wanted|asked|asks|ask"
    rf"|claimed|claims|claiming|pretend\w*|call(s|ed)?)\b"
    r"|\b(letters?|e-?mails?|texts?|messages?|notices?|pop-?ups?|voicemails?) (said|says|saying|claimed|claiming|told me)\b"
    r"|\bpretending to be\b"
    r"|\bif (anyone|anybody|someone|somebody|a caller|the caller|a stranger)\s+((\w+\s+){0,2}?)"
    r"(calls?|says?|asks?|tells?|wants?|claims?)\b", _I)
# A frame only once the call is clearly about scams: a friend's or family member's retelling.
_WEAK_FRAME = re.compile(
    r"\b(he|she|they|people|it|i)\s+((\w+\s+){0,1}?)(said|says|say|told (me|him|her|them|us|you)"
    r"|tells? (you|me|him|her|them|us)|wanted (me|us|him|her)|asks? (you|me|for)"
    r"|asked (me|us|him|her|you|for)|claimed|(was|were) pretending)\b", _I)
# The call is about scams: someone names one (not "this is not a scam") or retells a call.
_SCAM_TOPIC = re.compile(r"\b(scams?|scammers?|scammed|fraudsters?)\b"
                         r"|\bone of (those|these) (calls|letters|e-?mails|texts|messages|pop-?ups)\b"
                         r"|\b(it was|that'?s|it'?s) (a )?fake\b", _I)
# "This is not a scam" and "I know this sounds like a scam" are what scammers say to get ahead
# of doubt; neither makes the call about scams.
_TOPIC_NEGATED = re.compile(r"((\bnot|n'?t|\bno)\s+(\w+\s+){0,2}|\b(sounds?|seems?|looks?) like (a |an )?"
                            r"|\b(might|may|probably|will) think (it'?s |this is |that'?s )?(a |an )?)$", _I)
# A frame after the words: "Don't tell your family, they say."
_TRAILING_FRAME = re.compile(r",\s*(they|he|she|people)\s+(say|says|said|told me|tell you)\b\W*$", _I)
# Inside a retelling, only a sentence that asks something of the listener counts.
_DIRECT_ASK = re.compile(r"\b(you|your|ya)\b|\b(send|give|wire|pay|transfer|bring) (me|us)\b"
                         r"|^\W*(please\s+)?(send|buy|go|wire|give|transfer|pay|read|get|bring|meet|don'?t|do not|keep)\b", _I)
# "Who pays a bill with gift cards?" asks about it, it doesn't ask for it.
_WHO_QUESTION = re.compile(r"\bwho\s+(\w+\s+){0,4}$", _I)
# Gift cards as a present ("the boys want gift cards for Christmas").
_OCCASION = re.compile(r"\b(birthday|surprise|christmas|hanukkah|holiday|graduation|anniversary|wedding|stocking"
                       r"|presents?|party)\b", _I)
_PAYS_WITH_CARD = re.compile(r"\b(numbers?|codes?|scratch|pin|back of)\b", _I)
_YOU = re.compile(r"\b(you|your|ya)\b", _I)
# A sentence ends at . ! or ?, but not at the dot of a title ("Dr. Lee").
# "If anyone asks, say the gift cards are for your grandson" coaches the victim; it isn't a warning.
_COACHING = re.compile(r"\bif (anyone|anybody|someone|somebody|they|the (teller|bank|cashier|clerk)) "
                       r"(\w+ ){0,2}(asks?|calls?)\b[^.!?]{0,10}\b(just )?(say|tell (them|him|her))\b", _I)
_QUESTIONS_CALLER = re.compile(
    r"^\W*(are you (really |actually )?(from|with|calling from|the)|is this (really )?(the|my|a)\b"
    r"|is there (a|an) [^?]{0,40}\bfor you\b|do you (want|need) (gift cards|money|my|me to)|did you (just )?say"
    r"|you want me to)\b[^?]*\?\s*$", _I)
_SENTENCE_END = re.compile(r"(?<!\bDr)(?<!\bMr)(?<!\bMrs)(?<!\bMs)(?<!\bSt)(?<!\bJr)(?<!\bSr)[.!?]")


@dataclass(frozen=True)
class Context:
    """What the call so far is about. Built from every final line, both voices."""
    scam_talk: bool = False      # someone is warning about or retelling a scam
    reporting: bool = False      # within a few seconds of a retelling or warning ("a man said...")
    gift_occasion: bool = False  # a birthday, surprise or holiday came up: gift cards may be
                                 # presents and keeping it quiet may be a happy secret


def reports_scam(raw: str) -> bool:
    """This line retells or warns about a scam ("a man said...", "there's a scam going around").

    Questions don't count: a grandparent asking "Is this a scam?" must not switch the rules off
    for the caller's next lines (review 2026-11-14)."""
    text = raw.translate(_APOSTROPHES)
    for s in _sentences(text):
        if s.rstrip().endswith("?"):
            continue
        if _STRONG_FRAME.search(s) or any(not _TOPIC_NEGATED.search(s[:m.start()]) for m in _SCAM_TOPIC.finditer(s)):
            return True
    return False


def _sentences(text: str) -> list[str]:
    out, last = [], 0
    for m in _SENTENCE_END.finditer(text):
        out.append(text[last:m.end()])
        last = m.end()
    if text[last:].strip():
        out.append(text[last:])
    return out


def context_of(texts) -> Context:
    talk = gift = False
    for raw in texts:
        talk = talk or reports_scam(raw)
        gift = gift or bool(_OCCASION.search(raw))
    return Context(scam_talk=talk, gift_occasion=gift)


def _sentence_start(text: str, at: int) -> int:
    ends = [m.end() for m in _SENTENCE_END.finditer(text, 0, at)]
    return ends[-1] if ends else 0


def _reported(text: str, m: re.Match, ctx: Context) -> bool:
    start = _sentence_start(text, m.start())
    before = text[start:m.start()]
    if (_STRONG_FRAME.search(before) and not _COACHING.search(text[start:m.start()])) or _WHO_QUESTION.search(before):
        return True
    if ctx.scam_talk and _WEAK_FRAME.search(before):
        return True
    rest = _SENTENCE_END.search(text, m.end())
    sentence = text[start:rest.end() if rest else len(text)]
    # A quote retold over several sentences: "A man said Grandma, it's me. I need bail money."
    if _STRONG_FRAME.search(text[:start]) and not _YOU.search(sentence):
        return True
    if ctx.scam_talk and _TRAILING_FRAME.search(sentence):
        return True
    # Since captions come one sentence at a time, a retold quote ("A man said, Grandma, it's me.
    # I need bail money.") arrives in pieces. Right after a retelling, only a direct ask counts.
    if ctx.reporting and not _DIRECT_ASK.search(sentence):
        return True
    # The grandparent questioning the caller ("Are you from the bank?", "Do you want gift cards?",
    # "Is there a warrant out for you?"). With labels off these lines are scored too.
    if _QUESTIONS_CALLER.search(sentence):
        return True
    # An echo while talking about scams: "Gift cards?"
    if ctx.scam_talk and sentence.strip().endswith("?") and len(sentence.split()) <= 4:
        return True
    return False


def _gift_present(text: str, m: re.Match, ctx: Context) -> bool:
    return (ctx.gift_occasion and "gift" in m.group(0).lower()
            and not _PAYS_WITH_CARD.search(text))


def find_evidence(text: str, utterance_id: str, t_s: float,
                  context: Context | None = None) -> list[Evidence]:
    """Return at most one Evidence per tactic, using the first unguarded match.

    Matching runs on a cleaned copy (curly apostrophes made straight, fillers removed).
    Spans and quotes always point back into the original caption text.
    `context` says what the call so far is about (see context_of); None means nothing yet.
    """
    ctx = context or Context()
    norm, pos = _strip_fillers(text.translate(_APOSTROPHES))
    # "That's a scam" describes one, unless a scammer says "you might think it's a scam, but
    # go buy..." to get ahead of doubt: then the rest of the caption still counts.
    d = _DESCRIBES_SCAM.search(norm)
    if d and not _TOPIC_NEGATED.search(norm[:d.start()]) and not _DIRECT_ASK.search(norm[d.end():]):
        return []
    out: list[Evidence] = []
    for tactic, patterns in COMPILED.items():
        own = {T.SECRECY: _happy_secret, T.PAYMENT: _calls_the_number, T.URGENCY: _own_promise,
               T.THREAT: _already_blocked, T.IMPERSONATION: _someone_elses}.get(tactic)

        def skip(text, m, own=own, tactic=tactic):
            return (_reported(text, m, ctx) or (own is not None and own(text, m))
                    or (tactic is T.PAYMENT and _gift_present(text, m, ctx)))
        hit = _first_match(norm, patterns, skip)
        if hit:
            start, end, idx = hit
            start, end = pos[start], pos[end - 1] + 1  # back to the original text
            detail = None
            if tactic is T.IMPERSONATION:
                detail = "family" if idx < _FAMILY_PATTERNS else "official"
            out.append(Evidence(tactic, text[start:end], utterance_id, (start, end), "rule", t_s, detail))
    return out


# "Call the number on the back of your card" is what real banks (and our own card) tell you to do.
_CALL_BEFORE = re.compile(r"\b(call|dial|phone|ring)( the| that)?\s*$", _I)


def _calls_the_number(text: str, m: re.Match) -> bool:
    return bool(re.match(r"numbers?\b", m.group(0), _I) and _CALL_BEFORE.search(text[:m.start()])) \
        or bool(_OWN_OR_IN_PERSON.search(_sentence_of(text, m))) or _sends_to_you(text, m)


# "I'm going to send you the money with Zelle" is the speaker paying the listener, not an ask.
_PAY_APP = re.compile(r"\b(zelle|venmo|cash ?app|paypal|western union|moneygram)$", _I)
_I_DO_IT = re.compile(r"\b(i|i'?ll|i will|i'?m going to|i am going to|i'?m gonna|let me|i can|i just|i already)\s+$", _I)


def _sends_to_you(text: str, m: re.Match) -> bool:
    return bool(_PAY_APP.search(m.group(0)) and _I_DO_IT.search(text[:m.start()])
                and re.match(r"\w+ (you|it to you)\b", m.group(0), _I))


# Setting your own PIN, or bringing a card to the branch, isn't handing a number to the caller.
_OWN_OR_IN_PERSON = re.compile(r"\b(set|reset|change|create|choose|pick|update) (up )?(a |your )?(new )?(pin|password|passcode)\b"
                               r"|\b(when|if) you come in\b|\bat the (branch|bank|office|front desk)\b|\bin person\b|\bbring your\b", _I)


# A real fraud alert says the bank already stopped it: "someone tried to use your card and we blocked it".
_BLOCKED = re.compile(r"\b(we|we'?ve|we have|the bank|it was|it'?s been|that was|was) (already )?"
                      r"(blocked|stopped|declined|denied|caught|cancell?ed|frozen|flagged and blocked)\b"
                      r"|\byou don'?t (need|have) to do anything\b", _I)


# "My bank's fraud department called me" is someone talking about their own bank; a caller
# pretending says "your bank" or "the bank".
_OWNED_BY_SOMEONE = re.compile(r"\b(my|his|her|their)\s+$", _I)  # not "our": scammers say "our security team"


def _someone_elses(text: str, m: re.Match) -> bool:
    return bool(_OWNED_BY_SOMEONE.search(text[:m.start()]))


def _already_blocked(text: str, m: re.Match) -> bool:
    return bool(_BLOCKED.search(_sentence_of(text, m)))


def _sentence_of(text: str, m: re.Match) -> str:
    start = _sentence_start(text, m.start())
    rest = _SENTENCE_END.search(text, m.end())
    return text[start:rest.end() if rest else len(text)]


# "I'll fax it right now" promises the speaker's own action; it doesn't rush the listener.
# Only first person singular, never when the same sentence turns on the listener or threatens.
_OWN_PROMISE = re.compile(r"\b(i'?ll|i will|let me|i'?m going to|i am going to)\b.{0,60}$", _I)
_TURNS_ON_YOU = re.compile(r"\byou (need|have|must|got|gotta|should|better|can)\b|\byour (money|account|card|savings|bank)\b"
                           r"|\bunless\b|\bor else\b", _I)


def _own_promise(text: str, m: re.Match) -> bool:
    start = _sentence_start(text, m.start())
    rest = _SENTENCE_END.search(text, m.end())
    sentence = text[start:rest.end() if rest else len(text)]
    return bool(_OWN_PROMISE.search(text[start:m.start()])) and not _TURNS_ON_YOU.search(sentence)


def _happy_secret(text: str, m: re.Match) -> bool:
    return bool(_HAPPY_ANY.search(text) or _HAPPY_AFTER.search(text[m.end():]))


def _first_match(text: str, patterns: list[re.Pattern], skip=None) -> tuple[int, int, int] | None:
    """Earliest unguarded match: (start, end, index of the pattern that matched)."""
    best = None
    for idx, p in enumerate(patterns):
        for m in p.finditer(text):
            if _NEGATED.search(text[:m.start()]) or (skip and skip(text, m)):
                continue
            if best is None or m.start() < best[0]:
                best = (m.start(), m.end(), idx)
            break
    return best
