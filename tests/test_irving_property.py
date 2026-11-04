"""Property-based and invariant tests for Irving's (1985) Stable Roommates Algorithm.

Verifies:
1. Mathematical stability: 0 blocking pairs on all solved instances.
2. Honest failure: returns 'no stable matching exists' when preference deadlocks occur.
3. Determinism: identical pairings regardless of initial dict insertion order.
4. Randomized pool invariance: randomized preference profiles never produce a blocking pair.
"""
from __future__ import annotations

import random
import pytest

from app.matching.irving import find_blocking_pairs, irving_stable_roommates


def test_irving_paper_example():
    """Verify the canonical 6-person instance from Irving's 1985 paper."""
    prefs = {
        "1": ["3", "4", "2", "6", "5"],
        "2": ["6", "5", "4", "1", "3"],
        "3": ["2", "4", "5", "1", "6"],
        "4": ["5", "2", "3", "6", "1"],
        "5": ["3", "1", "2", "4", "6"],
        "6": ["5", "1", "3", "4", "2"],
    }
    has_match, matches, reason = irving_stable_roommates(list(prefs.keys()), prefs)
    assert has_match is True
    assert len(matches) == 6
    assert all(matches[matches[p]] == p for p in prefs)
    
    # Assert strictly zero blocking pairs
    blocking = find_blocking_pairs(matches, prefs)
    assert len(blocking) == 0


def test_irving_unsolvable_cycle_reported_honestly():
    """Verify that preference deadlocks honestly report 'no stable matching exists'."""
    # Classic 4-roommate cyclical deadlock where every possible pairing is blocked
    prefs = {
        "1": ["2", "3", "4"],
        "2": ["3", "1", "4"],
        "3": ["1", "2", "4"],
        "4": ["1", "2", "3"],
    }
    has_match, matches, reason = irving_stable_roommates(["1", "2", "3", "4"], prefs)
    assert has_match is False
    assert matches == {}
    assert "no stable matching exists" in reason.lower()


def test_irving_deterministic_proposer_order():
    """Verify that proposer order is strictly deterministic (sorted order)."""
    prefs = {
        "a": ["b", "c", "d"],
        "b": ["a", "d", "c"],
        "c": ["d", "a", "b"],
        "d": ["c", "b", "a"],
    }
    # Run with different input orders
    _, m1, _ = irving_stable_roommates(["a", "b", "c", "d"], prefs)
    _, m2, _ = irving_stable_roommates(["d", "c", "b", "a"], prefs)
    _, m3, _ = irving_stable_roommates(["c", "a", "d", "b"], prefs)

    assert m1 == m2 == m3


def test_random_pools_zero_blocking_pairs_property():
    """Property test across 50 random preference pools of sizes 4, 6, and 8.

    Asserts that whenever Irving's algorithm returns True, the matching
    has STRICTLY ZERO blocking pairs.
    """
    solved = 0
    unsolved = 0

    for pool_size in [4, 6, 8]:
        for seed in range(20):
            rng = random.Random(seed * 100 + pool_size)
            pids = [f"cand_{i}" for i in range(pool_size)]
            
            # Generate random complete strict preference ranking for each candidate
            prefs = {}
            for p in pids:
                others = [x for x in pids if x != p]
                rng.shuffle(others)
                prefs[p] = others

            has_match, matches, reason = irving_stable_roommates(pids, prefs)

            if has_match:
                solved += 1
                assert len(matches) == pool_size
                assert all(matches[matches[p]] == p for p in pids)
                
                # INVARIANT: Zero blocking pairs!
                blocking = find_blocking_pairs(matches, prefs)
                assert len(blocking) == 0, f"Violation: blocking pairs found {blocking} in pool {pids}"
            else:
                unsolved += 1
                assert matches == {}
                assert "no stable matching exists" in reason.lower()

    # Verify both outcomes occurred and were handled honestly
    assert solved > 0
    assert unsolved > 0
