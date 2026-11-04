"""Matching engines: Irving's Stable Roommates and Deferred Acceptance."""
from . import gale_shapley, irving
from .gale_shapley import StableMatch, StableMatchingResult, compute_stable_matching
from .irving import find_blocking_pairs, irving_stable_roommates

__all__ = [
    "StableMatch",
    "StableMatchingResult",
    "compute_stable_matching",
    "irving_stable_roommates",
    "find_blocking_pairs",
    "gale_shapley",
    "irving",
]
