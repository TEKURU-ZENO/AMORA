"""Shared compatibility signals between two analyses (used by both engines and screening)."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..models import Analysis

# A dealbreaker of A is triggered when B shows any of these traits.
DEALBREAKER_TRIGGERS = {
    "Constant need to be out and performing socially": {"social", "spontaneous"},
    "Someone who never wants to leave their comfort zone": {"homebody"},
    "Flaky plans and chronic lateness": {"spontaneous"},
    "Feeling held back or resented for their goals": set(),
    "Emotional unavailability": set(),
}


@dataclass
class Compat:
    shared_hobbies: list[str] = field(default_factory=list)
    shared_interests: list[str] = field(default_factory=list)
    shared_values: list[str] = field(default_factory=list)
    energy_match: bool = True
    dealbreakers_a: list[str] = field(default_factory=list)  # A's dealbreakers that B triggers
    dealbreakers_b: list[str] = field(default_factory=list)
    prior: float = 0.0  # 0..10


def _energy(a: Analysis) -> str:
    return (a.lifestyle or {}).get("social energy", "balanced")


def compute(a: Analysis, b: Analysis) -> Compat:
    sh = sorted(set(a.hobbies) & set(b.hobbies))
    si = sorted(set(a.interests) & set(b.interests))
    sv = sorted(set(a.values) & set(b.values))
    ea, eb = _energy(a), _energy(b)
    energy_match = ea == eb or "balanced" in (ea, eb)
    ta, tb = set(a.personality), set(b.personality)
    dba = [d for d in a.dealbreakers if DEALBREAKER_TRIGGERS.get(d, set()) & tb]
    dbb = [d for d in b.dealbreakers if DEALBREAKER_TRIGGERS.get(d, set()) & ta]
    complementary = len((ta ^ tb) & {"calm", "expressive", "analytical", "creative", "nurturing"})
    prior = (2.2 * len(sh) + 1.2 * len(si) + 1.0 * len(sv) + 0.4 * complementary
             + (1.0 if energy_match else -1.0) - 2.5 * (len(dba) + len(dbb)))
    prior = max(0.0, min(10.0, 2.5 + prior))
    return Compat(sh, si, sv, energy_match, dba, dbb, round(prior, 2))
