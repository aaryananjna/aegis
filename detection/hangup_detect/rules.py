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
        r"\b((your|the) )?bank'?s? (fraud|security) (department|team|division)\b",
        r"\b(public defender|your (grandson'?s|lawyer|attorney))\b",
        # FTC: prize and lottery callers, fake FTC/FBI agents with badge numbers
        r"\byou('ve| have) (just )?won\b(?=.{0,40}\b(lottery|sweepstakes|prize|million|grant)\b)",
        r"\b(federally supervised lottery|publishers clearing house)\b",
        r"\b(agent|investigator|officer) (with|from) the (federal trade commission|ftc|fbi)\b",
        r"\bbadge number\b",
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
        r"\b(courier|driver|someone) (will|to) (come )?(pick up|collect)\b",
        r"\b(bail money|bail bond|(pay|post|make) (my |the |his |her )?bail|bail is set)\b",
    ],
    T.THREAT: [
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
        r"\b(anydesk|teamviewer|ultraviewer|logmein|supremo)\b",
        r"\bremote (access|desktop|support|session)\b",
        r"\b(take control of|get into|connect to) your (computer|phone|screen)\b",
        r"\bshare your screen\b",
        r"\bpress (the )?windows (key|and r)\b",
        # Bank "never" lists: asking for a code or credentials
        r"\b(read|give|tell) me (the|your) (verification |security |one[- ]time )?(code|pin|password)\b",
    ],
    T.DISTRESS: [
        r"\bi'?m (so )?(scared|terrified|in trouble|in big trouble|hurt|bleeding|crying)\b",
        r"\bi (got|was) in (an|a car) accident\b",
        r"(?#exact)\b(please help( me)?|i need your help)\b",  # "i need help" is everyday talk
        r"\b(i'?m|he'?s|she'?s) in the hospital\b",
        r"\bbroke my (nose|arm|leg|wrist)\b",
        r"\bpregnant woman\b",  # AARP grandparent scam
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
_NEGATED = re.compile(r"\b(not|never|no)\s+(\w+\s+){0,2}$", _I)
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


def find_evidence(text: str, utterance_id: str, t_s: float) -> list[Evidence]:
    """Return at most one Evidence per tactic, using the first unguarded match.

    Matching runs on a cleaned copy (curly apostrophes made straight, fillers removed).
    Spans and quotes always point back into the original caption text.
    """
    norm, pos = _strip_fillers(text.translate(_APOSTROPHES))
    if _DESCRIBES_SCAM.search(norm):
        return []
    out: list[Evidence] = []
    for tactic, patterns in COMPILED.items():
        skip = _happy_secret if tactic is T.SECRECY else None
        hit = _first_match(norm, patterns, skip)
        if hit:
            start, end, idx = hit
            start, end = pos[start], pos[end - 1] + 1  # back to the original text
            detail = None
            if tactic is T.IMPERSONATION:
                detail = "family" if idx < _FAMILY_PATTERNS else "official"
            out.append(Evidence(tactic, text[start:end], utterance_id, (start, end), "rule", t_s, detail))
    return out


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
