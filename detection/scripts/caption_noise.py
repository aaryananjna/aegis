"""Caption damage check: python scripts/caption_noise.py (run inside detection/).

Runs every dev call plus the demo calls through simulated speech-to-text mistakes and
prints, per kind of damage, which scams stop reaching HIGH and which normal calls false alarm.
All synthetic; it shows weak spots, not real-world accuracy.
"""
import re, sys, random
sys.path.insert(0, ".")
from pathlib import Path
from hangup_detect.replay import parse_call, replay

def lower_nopunct(t): return re.sub(r"[.,!?;:]", "", t).lower()
EXPAND = {"it's": "it is", "don't": "do not", "there's": "there is", "i'm": "i am", "you've": "you have",
          "can't": "cannot", "you'll": "you will", "we'll": "we will", "won't": "will not", "i've": "i have"}
def expand(t):
    return re.sub(r"\b(" + "|".join(re.escape(k) for k in EXPAND) + r")\b", lambda m: EXPAND[m.group(1).lower()], t, flags=re.I)
def no_apostrophe(t): return t.replace("'", "")
FILL = ["um", "uh", "like", "you know"]
def fillers(t):
    rnd = random.Random(len(t)); w = t.split(); out = []
    for x in w:
        out.append(x)
        if rnd.random() < 0.2: out.append(rnd.choice(FILL))
    return " ".join(out)
MISHEAR = {"gift cards": "gift guards", "bail": "bale", "wire": "why her", "bitcoin": "bit coin",
           "anydesk": "any desk", "grandson": "grand son", "grandma": "grand ma", "nana": "nanna"}
def mishear(t):
    for a, b in MISHEAR.items():
        t = re.sub(re.escape(a), b, t, flags=re.I)
    return t
def drop_words(t):
    rnd = random.Random(len(t) * 7)
    return " ".join(x for x in t.split() if rnd.random() > 0.12)

DAMAGE = {"clean": lambda t: t, "lower_nopunct": lower_nopunct, "expanded": expand,
          "no_apostrophe": no_apostrophe, "fillers": fillers, "mishear": mishear, "drop_12pct": drop_words,
          "all": lambda t: drop_words(mishear(fillers(no_apostrophe(lower_nopunct(t)))))}

files = sorted(Path("eval/calls/dev").glob("*.call")) + [Path("demo/demo-scam.call"), Path("demo/demo-real.call")]
for name, fn in DAMAGE.items():
    miss, fa = [], []
    for f in files:
        call = parse_call(f.read_text())
        call.lines[:] = [l.__class__(**{**l.__dict__, "text": fn(l.text)}) for l in call.lines]
        evs = replay(call)
        high = any(e["type"] == "risk" and e["level"] == "high" for e in evs)
        label = call.headers["label"]
        if label == "scam" and not high: miss.append(call.headers["id"])
        if label == "benign" and high: fa.append(call.headers["id"])
    print(f"{name:14s} missed {len(miss)}/{sum(1 for f in files if "scam" in f.name)} {miss}  false alarms {len(fa)}/{sum(1 for f in files if "scam" not in f.name)} {fa}")
