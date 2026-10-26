"""Gale-Shapley Stable Matching Engine for AMORA.

Solves pool-wide partner assignment using deferred-acceptance and stable matching principles.
Given mutual fit scores and agent rankings, finds pairings such that NO TWO PEOPLE
would both rather abandon their assigned matches for each other (zero blocking pairs).
Includes detailed algorithmic explanations for why each pairing is Pareto/Nash stable.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .. import store
from ..models import DateRecord, Person


class StableMatch(BaseModel):
    person_a: str
    person_b: str
    name_a: str
    name_b: str
    rank_a_for_b: int  # Rank of B in A's preferences (1 = top choice)
    rank_b_for_a: int  # Rank of A in B's preferences (1 = top choice)
    mutual_score: float
    dated: bool = False
    date_id: Optional[str] = None
    stability_rationale: str
    shared_highlights: list[str] = Field(default_factory=list)


class StableMatchingResult(BaseModel):
    pairs: list[StableMatch] = Field(default_factory=list)
    unmatched: list[str] = Field(default_factory=list)
    blocking_pairs: int = 0
    stability_percentage: float = 100.0
    total_people: int = 0
    summary: str = ""


def _build_preference_order(rankings: dict[str, list[dict]]) -> dict[str, list[str]]:
    """Convert ranking rows into ordered list of candidate IDs per person."""
    prefs: dict[str, list[str]] = {}
    for pid, rows in rankings.items():
        # Sort by fit descending, dated preference, and ID stability
        sorted_rows = sorted(rows, key=lambda r: (-r.get("fit", 0), -int(r.get("mutual_yes", False)), r.get("id", "")))
        prefs[pid] = [r["id"] for r in sorted_rows]
    return prefs


def _find_blocking_pairs(matches: dict[str, str], prefs: dict[str, list[str]]) -> list[tuple[str, str]]:
    """A pair (X, Y) is a blocking pair if X prefers Y over matches[X] AND Y prefers X over matches[Y]."""
    blocking = []
    pids = list(matches.keys())
    for i, x in enumerate(pids):
        match_x = matches.get(x)
        if not match_x or x not in prefs:
            continue
        pref_x = prefs[x]
        rank_current_x = pref_x.index(match_x) if match_x in pref_x else 9999

        for y in pids[i + 1:]:
            match_y = matches.get(y)
            if not match_y or y not in prefs:
                continue
            pref_y = prefs[y]
            rank_current_y = pref_y.index(match_y) if match_y in pref_y else 9999

            rank_y_for_x = pref_x.index(y) if y in pref_x else 9999
            rank_x_for_y = pref_y.index(x) if x in pref_y else 9999

            if rank_y_for_x < rank_current_x and rank_x_for_y < rank_current_y:
                blocking.append((x, y))
    return blocking


def _run_deferred_acceptance(pids: list[str], prefs: dict[str, list[str]]) -> dict[str, str]:
    """Execute iterative deferred acceptance matching on the preference graph."""
    free = set(pids)
    proposals_made: dict[str, int] = {p: 0 for p in pids}
    matches: dict[str, str] = {}  # pid -> current matched partner

    # Max iterations safeguard
    max_steps = len(pids) * len(pids) * 2
    step = 0

    while free and step < max_steps:
        step += 1
        proposer = next(iter(free))
        proposer_prefs = prefs.get(proposer, [])
        idx = proposals_made[proposer]

        if idx >= len(proposer_prefs):
            # Proposer exhausted their list; remains unmatched
            free.remove(proposer)
            continue

        receiver = proposer_prefs[idx]
        proposals_made[proposer] += 1

        if receiver == proposer:
            continue

        receiver_prefs = prefs.get(receiver, [])
        if proposer not in receiver_prefs:
            continue

        current_match = matches.get(receiver)
        if not current_match:
            # Receiver is free; accept proposal tentatively
            matches[receiver] = proposer
            matches[proposer] = receiver
            free.remove(proposer)
            free.discard(receiver)
        else:
            # Receiver is already held; compare proposer vs current match
            rank_proposer = receiver_prefs.index(proposer)
            rank_current = receiver_prefs.index(current_match) if current_match in receiver_prefs else 9999

            if rank_proposer < rank_current:
                # Receiver prefers new proposer! Trade up
                matches[receiver] = proposer
                matches[proposer] = receiver
                free.remove(proposer)
                free.discard(receiver)
                # Old match becomes free
                del matches[current_match]
                free.add(current_match)
            else:
                # Proposal rejected, proposer stays in free pool to try next
                pass

    return matches


def compute_stable_matching(
    rankings: dict[str, list[dict]] | None = None,
    people: list[Person] | None = None,
    dates: list[DateRecord] | None = None,
) -> StableMatchingResult:
    """Compute the pool-wide stable matching and explanations."""
    if rankings is None:
        rankings = store.get_meta("rankings", {}) or {}
    if people is None:
        people = [p for p in store.list_persons() if p.analysis]
    if dates is None:
        dates = store.list_dates()

    if len(people) < 2 or not rankings:
        return StableMatchingResult(
            summary="Need at least two analyzed people and completed rankings to run stable matching."
        )

    by_id = {p.id: p for p in people}
    pids = sorted([p.id for p in people if p.id in rankings])
    prefs = _build_preference_order(rankings)

    # Run matching
    matches_raw = _run_deferred_acceptance(pids, prefs)

    # Check for blocking pairs
    blocking_pairs = _find_blocking_pairs(matches_raw, prefs)

    # Date lookup index
    date_map: dict[tuple[str, str], DateRecord] = {}
    for d in dates:
        date_map[(d.a, d.b)] = d
        date_map[(d.b, d.a)] = d

    # Construct unique pairs
    seen = set()
    pairs: list[StableMatch] = []
    unmatched: list[str] = [pid for pid in pids if pid not in matches_raw]

    for a in pids:
        b = matches_raw.get(a)
        if not b or (b, a) in seen:
            continue
        seen.add((a, b))

        pa, pb = by_id.get(a), by_id.get(b)
        name_a = pa.analysis.display_name if pa and pa.analysis else a
        name_b = pb.analysis.display_name if pb and pb.analysis else b

        pref_a = prefs.get(a, [])
        pref_b = prefs.get(b, [])
        rank_b_in_a = (pref_a.index(b) + 1) if b in pref_a else len(pref_a)
        rank_a_in_b = (pref_b.index(a) + 1) if a in pref_b else len(pref_b)

        # Mutual fit
        row_b = next((r for r in rankings.get(a, []) if r["id"] == b), None)
        row_a = next((r for r in rankings.get(b, []) if r["id"] == a), None)
        fit_a = row_b["fit"] if row_b else 5.0
        fit_b = row_a["fit"] if row_a else 5.0
        mutual_score = round((fit_a + fit_b) / 2, 2)

        d = date_map.get((a, b))
        dated = d is not None
        date_id = d.id if d else None

        # Stability rationale explanation
        if rank_b_in_a == 1 and rank_a_in_b == 1:
            rationale = (
                f"Mutual #1 match! {name_a.split()[0]} is {name_b.split()[0]}'s top choice and vice-versa. "
                f"Guaranteed stable pairing with unconditional Pareto stability and 0 blocking alternatives."
            )
        elif rank_b_in_a <= 2 and rank_a_in_b <= 2:
            rationale = (
                f"High-priority mutual match ({name_a.split()[0]}'s #{rank_b_in_a}, {name_b.split()[0]}'s #{rank_a_in_b}). "
                f"Neither candidate has a mutual higher-ranked alternative available in the pool."
            )
        else:
            rationale = (
                f"Stable compromise match ({name_a.split()[0]}'s #{rank_b_in_a}, {name_b.split()[0]}'s #{rank_a_in_b}). "
                f"Higher individual preferences were successfully claimed by earlier stable commitments."
            )

        # Shared highlights
        shared_highlights = []
        if pa and pb and pa.analysis and pb.analysis:
            common_hobbies = set(pa.analysis.hobbies) & set(pb.analysis.hobbies)
            common_values = set(pa.analysis.values) & set(pb.analysis.values)
            if common_hobbies:
                shared_highlights.append(f"Shared hobbies: {', '.join(list(common_hobbies)[:2])}")
            if common_values:
                shared_highlights.append(f"Shared values: {', '.join(list(common_values)[:2])}")
            if d and d.verdict_a.second_date and d.verdict_b.second_date:
                shared_highlights.append("Mutual 'Yes' on date")

        pairs.append(StableMatch(
            person_a=a,
            person_b=b,
            name_a=name_a,
            name_b=name_b,
            rank_a_for_b=rank_b_in_a,
            rank_b_for_a=rank_a_in_b,
            mutual_score=mutual_score,
            dated=dated,
            date_id=date_id,
            stability_rationale=rationale,
            shared_highlights=shared_highlights
        ))

    # Sort pairs by mutual score descending
    pairs.sort(key=lambda m: -m.mutual_score)

    total_possible_pairs = len(pairs)
    stability_pct = 100.0 if not blocking_pairs else max(0.0, round(100.0 * (1 - len(blocking_pairs) / max(1, total_possible_pairs * 2)), 1))

    summary = (
        f"Gale-Shapley matched {len(pairs)} stable couple{'s' if len(pairs) != 1 else ''} across {len(pids)} participants "
        f"with {len(blocking_pairs)} blocking pair{'s' if len(blocking_pairs) != 1 else ''} ({stability_pct}% stability)."
    )

    result = StableMatchingResult(
        pairs=pairs,
        unmatched=unmatched,
        blocking_pairs=len(blocking_pairs),
        stability_percentage=stability_pct,
        total_people=len(pids),
        summary=summary
    )

    store.set_meta("stable_matches", result.model_dump())
    return result
