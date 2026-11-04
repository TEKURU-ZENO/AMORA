"""Irving's (1985) Algorithm for the Stable Roommates Problem (SRP).

Reference:
Robert W. Irving, "An Efficient Algorithm for the "Stable Roommates" Problem",
Journal of Algorithms, 6(4): 577-595, 1985.

Features:
- Deterministic proposer ordering (lexicographical sorting of participant IDs).
- Complete two-phase algorithm (Phase 1 proposal reduction, Phase 2 rotation elimination).
- Returns honest failure if no stable matching exists for the preference profile.
- Zero stability rhetoric: purely factual algorithmic verification.
"""
from __future__ import annotations

import collections
from typing import Optional


def find_blocking_pairs(matches: dict[str, str], prefs: dict[str, list[str]]) -> list[tuple[str, str]]:
    """A pair (X, Y) blocks a matching if X prefers Y over matches[X] and Y prefers X over matches[Y]."""
    blocking = []
    pids = sorted(matches.keys())
    for i, x in enumerate(pids):
        match_x = matches.get(x)
        if not match_x or x not in prefs:
            continue
        pref_x = prefs[x]
        if match_x not in pref_x:
            continue
        rank_current_x = pref_x.index(match_x)

        for y in pids[i + 1:]:
            match_y = matches.get(y)
            if not match_y or y not in prefs:
                continue
            pref_y = prefs[y]
            if match_y not in pref_y:
                continue
            rank_current_y = pref_y.index(match_y)

            if y in pref_x and x in pref_y:
                rank_y_for_x = pref_x.index(y)
                rank_x_for_y = pref_y.index(x)
                if rank_y_for_x < rank_current_x and rank_x_for_y < rank_current_y:
                    blocking.append((x, y))
    return blocking


def irving_stable_roommates(pids: list[str], prefs: dict[str, list[str]]) -> tuple[bool, dict[str, str], str]:
    """Execute Irving's (1985) algorithm for the Stable Roommates Problem.

    Args:
        pids: List of participant IDs.
        prefs: Mapping of participant ID -> ordered list of other participants by preference.

    Returns:
        (has_stable_matching: bool, matches: dict[str, str], reason: str)
    """
    sorted_pids = sorted(pids)
    n = len(sorted_pids)
    if n < 2:
        return False, {}, "Need at least 2 participants for stable matching."
    if n % 2 != 0:
        return False, {}, "No stable matching exists: odd number of participants."

    # Validate preference lists
    for p in sorted_pids:
        if p not in prefs:
            return False, {}, f"No stable matching exists: missing preferences for {p}."

    # Initial reduced preference lists
    reduced: dict[str, list[str]] = {
        p: [c for c in prefs[p] if c in sorted_pids and c != p]
        for p in sorted_pids
    }

    # Original rank mapping: rank[x][y] = 0-indexed position of y in x's preferences
    rank: dict[str, dict[str, int]] = {}
    for p in sorted_pids:
        rank[p] = {other: idx for idx, other in enumerate(prefs[p])}

    # ==================== Phase 1: Propose and Reject ====================
    # Deterministic proposer queue: sorted order
    free = collections.deque(sorted_pids)
    held_by: dict[str, Optional[str]] = {p: None for p in sorted_pids}

    def reject(receiver: str, cand: str) -> bool:
        """Receiver rejects cand. Both remove each other. Returns False if any list becomes empty."""
        if cand in reduced[receiver]:
            reduced[receiver].remove(cand)
        if receiver in reduced[cand]:
            reduced[cand].remove(receiver)
        if not reduced[receiver] or not reduced[cand]:
            return False
        return True

    while free:
        proposer = free.popleft()

        while reduced[proposer]:
            receiver = reduced[proposer][0]
            current_holder = held_by[receiver]

            if current_holder is None:
                # Receiver holds proposal
                held_by[receiver] = proposer
                # Receiver rejects all candidates worse than proposer in original preferences
                p_rank = rank[receiver].get(proposer, 9999)
                worse = [c for c in list(reduced[receiver]) if rank[receiver].get(c, 9999) > p_rank]
                for w in worse:
                    if not reject(receiver, w):
                        return False, {}, f"No stable matching exists: preference list exhausted for {w} in Phase 1."
                break
            elif rank[receiver].get(proposer, 9999) < rank[receiver].get(current_holder, 9999):
                # Receiver prefers proposer over current_holder
                held_by[receiver] = proposer
                free.append(current_holder)
                # Receiver rejects current_holder and everyone worse than proposer
                p_rank = rank[receiver].get(proposer, 9999)
                worse = [c for c in list(reduced[receiver]) if rank[receiver].get(c, 9999) > p_rank]
                for w in worse:
                    if not reject(receiver, w):
                        return False, {}, f"No stable matching exists: preference list exhausted for {w} in Phase 1."
                break
            else:
                # Receiver prefers current holder; rejects proposer
                if not reject(receiver, proposer):
                    return False, {}, f"No stable matching exists: preference list exhausted for {proposer} in Phase 1."

        if not reduced[proposer] and held_by[proposer] is None:
            return False, {}, f"No stable matching exists: {proposer} exhausted all candidates without holding or being held."

    # Post-Phase 1 verification
    for p in sorted_pids:
        if not reduced[p]:
            return False, {}, f"No stable matching exists: empty preference list for {p} after Phase 1."

    # If every list is already length 1, we are done
    if all(len(reduced[p]) == 1 for p in sorted_pids):
        matches = {p: reduced[p][0] for p in sorted_pids}
        if all(matches[matches[p]] == p for p in sorted_pids):
            blocking = find_blocking_pairs(matches, prefs)
            if not blocking:
                return True, matches, "Stable matching found via Irving Phase 1 reduction."

    # ==================== Phase 2: Rotation Elimination ====================
    max_steps = n * n * 4
    step = 0

    while any(len(reduced[p]) > 1 for p in sorted_pids) and step < max_steps:
        step += 1
        # Find first person with >= 2 candidates deterministically
        start_p = next(p for p in sorted_pids if len(reduced[p]) >= 2)

        p_list = [start_p]
        q_list = []
        visited = {start_p: 0}

        curr = start_p
        while True:
            # q_i is the second candidate in curr's list
            q_i = reduced[curr][1]
            q_list.append(q_i)

            # p_{i+1} is the last candidate in q_i's list
            p_next = reduced[q_i][-1]

            if p_next in visited:
                # Cycle identified from index cycle_idx to current
                cycle_idx = visited[p_next]
                p_rot = p_list[cycle_idx:]
                q_rot = q_list[cycle_idx:]
                break
            else:
                visited[p_next] = len(p_list)
                p_list.append(p_next)
                curr = p_next

        # Eliminate rotation: each q_k rejects p_{k+1} and any candidates worse than p_k
        r = len(p_rot)
        for k in range(r):
            q_k = q_rot[k]
            p_k1 = p_rot[(k + 1) % r]
            p_k = p_rot[k]

            p_k_rank = rank[q_k].get(p_k, 9999)
            worse = [c for c in list(reduced[q_k]) if rank[q_k].get(c, 9999) > p_k_rank]
            if p_k1 not in worse and p_k1 in reduced[q_k]:
                worse.append(p_k1)

            for w in worse:
                if not reject(q_k, w):
                    return False, {}, f"No stable matching exists: list exhausted for {w} during Phase 2 rotation elimination."

    # Final validation
    if any(len(reduced[p]) != 1 for p in sorted_pids):
        return False, {}, "No stable matching exists: preferences could not be reduced to singletons."

    matches = {p: reduced[p][0] for p in sorted_pids}
    if not all(matches[matches[p]] == p for p in sorted_pids):
        return False, {}, "No stable matching exists: matching is not symmetric."

    blocking = find_blocking_pairs(matches, prefs)
    if blocking:
        return False, {}, f"No stable matching exists: internal blocking pairs detected: {blocking}."

    return True, matches, "Stable matching found via Irving Phase 2 rotation elimination."
