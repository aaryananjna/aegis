import math
import random

import pytest

from hangup_detect.config import Config
from hangup_detect.risk import RiskModel, next_level
from hangup_detect.types import Evidence, Tactic as T

CFG = Config()


def ev(tactic, t=0.0, source="rule", uid="u"):
    return Evidence(tactic, "q", uid, (0, 1), source, t)


def model(*evs):
    m = RiskModel(CFG)
    for e in evs:
        m.add(e)
    return m


def sig(x):
    return 1 / (1 + math.exp(-x))


# Expected alert points from the plan (fresh hits, t=0)
@pytest.mark.parametrize("tactics,expected", [
    ([T.IMPERSONATION, T.PAYMENT], sig(1.7)),
    ([T.IMPERSONATION, T.SECRECY, T.URGENCY], sig(1.5)),
    ([T.REMOTE_ACCESS, T.IMPERSONATION], sig(1.7)),
    ([T.IMPERSONATION, T.URGENCY], sig(-1.0)),
])
def test_expected_points(tactics, expected):
    m = model(*[ev(t) for t in tactics])
    assert m.score(0.0) == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize("tactic", list(T))
def test_single_hit_stays_low(tactic):
    m = model(ev(tactic))
    assert m.update_level(0.0) == "low"


def test_payment_twice_is_elevated_not_high():
    m = model(ev(T.PAYMENT, uid="a"), ev(T.PAYMENT, uid="b"))
    assert m.score(0.0) == pytest.approx(0.5)
    assert m.update_level(0.0) == "elevated"


def test_ten_urgency_repeats_stay_low():
    m = model(*[ev(T.URGENCY, uid=str(i)) for i in range(10)])
    assert m.score(0.0) == pytest.approx(sig(-3 + 0.8 + 0.4))
    assert m.update_level(0.0) == "low"


def test_decay_half_life():
    m = model(ev(T.PAYMENT))
    assert m.score(120.0) == pytest.approx(sig(-3 + 1.0))


def test_old_evidence_frees_slots():
    m = model(ev(T.URGENCY, 0.0, uid="a"), ev(T.URGENCY, 0.0, uid="b"))
    m.add(ev(T.URGENCY, 700.0, uid="c"))
    assert m.score(700.0) == pytest.approx(sig(-3 + 0.8))


def test_score_is_pure():
    m = model(ev(T.IMPERSONATION), ev(T.PAYMENT))
    assert m.level == "low"
    m.score(0.0)
    m.contributions(0.0)
    assert m.level == "low"
    assert m.update_level(0.0) == "high"


# LLM supplement
def test_llm_only_adds_above_rule():
    m = model(ev(T.PAYMENT), ev(T.PAYMENT, source="llm"))
    # llm 0.7*2=1.4 < rule 2.0, so it adds nothing
    assert m.score(0.0) == pytest.approx(sig(-1.0))


def test_llm_proportional_cap_example():
    m = model(ev(T.PAYMENT, source="llm"), ev(T.SECRECY, source="llm"))
    c = m.contributions(0.0)["llm"]
    assert c["payment"] == pytest.approx(0.857142857, abs=1e-6)
    assert c["secrecy"] == pytest.approx(0.642857143, abs=1e-6)


def test_llm_alone_cannot_reach_high():
    # every tactic twice from the LLM: the +1.5 cap also shrinks each tactic's
    # strength, so combos shrink too. Upper bound is sig(-3 + 1.5 + 2.0).
    m = model(*[ev(t, source="llm", uid=f"{t.value}{k}") for t in T for k in range(2)])
    assert m.score(0.0) < sig(0.5) < CFG.enter_high
    assert m.update_level(0.0) != "high"


def test_combo_cap():
    m = model(*[ev(t) for t in T])
    assert sum(m.contributions(0.0)["combos"].values()) == pytest.approx(2.0)


# Transition table, every row and exact boundary
@pytest.mark.parametrize("prev,score,has_rule,want", [
    ("low", 0.80, True, "high"),
    ("elevated", 0.80, True, "high"),
    ("low", 0.80, False, "elevated"),
    ("high", 0.85, False, "elevated"),
    ("high", 0.60, True, "high"),
    ("high", 0.5999, True, "elevated"),
    ("high", 0.35, True, "elevated"),
    ("high", 0.3499, True, "low"),
    ("elevated", 0.35, True, "elevated"),
    ("elevated", 0.3499, True, "low"),
    ("low", 0.50, True, "elevated"),
    ("low", 0.4999, True, "low"),
    ("elevated", 0.79, True, "elevated"),
])
def test_transition_table(prev, score, has_rule, want):
    assert next_level(prev, score, has_rule, CFG) == want


def test_hysteresis_no_flicker():
    m = model(ev(T.IMPERSONATION), ev(T.PAYMENT))
    assert m.update_level(0.0) == "high"
    # decays slowly through 0.80..0.60 and must stay high there
    t = 0.0
    while m.score(t) >= 0.60:
        assert m.update_level(t) == "high"
        t += 1.0
    assert m.update_level(t) in ("elevated", "low")


def test_combos_fade_smoothly():
    m = model(ev(T.IMPERSONATION), ev(T.SECRECY), ev(T.PAYMENT), ev(T.URGENCY))
    prev = m.score(0.0)
    for t in range(1, 900):
        s = m.score(float(t))
        assert abs(s - prev) <= 0.05
        prev = s


def test_invariant3_llm_never_lowers_score():
    rnd = random.Random(7)
    tactics = list(T)
    for _ in range(500):
        full, rules = RiskModel(CFG), RiskModel(CFG)
        for i in range(rnd.randint(1, 12)):
            e = Evidence(rnd.choice(tactics), "q", str(i), (0, 1),
                         rnd.choice(["rule", "llm"]), rnd.uniform(0, 300))
            full.add(e)
            if e.source == "rule":
                rules.add(e)
        for now in (0.0, 100.0, 300.0, 500.0, 900.0):
            assert full.score(now) >= rules.score(now) - 1e-12
            assert full.score(now, include_llm=False) == pytest.approx(rules.score(now))


def test_clear_resets():
    m = model(ev(T.IMPERSONATION), ev(T.PAYMENT))
    m.update_level(0.0)
    m.clear()
    assert m.score(0.0) == pytest.approx(sig(-3)) and m.level == "low"
