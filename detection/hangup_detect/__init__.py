"""Aegis detection: scam tactic rules, risk score and counter-moves."""
from .config import Config
from .pipeline import Detector
from .types import Evidence, Segment, Tactic, make_segment

__all__ = ["Config", "Detector", "Evidence", "Segment", "Tactic", "make_segment"]
