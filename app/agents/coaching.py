"""Agent Coaching & Feedback Engine.

Provides:
1. Pre-date coaching directives (instructions given by human to their agent).
2. Post-date human feedback loop (human corrects the agent, updates brief, modifies preferences/dealbreakers, re-ranks).
3. Cross-date learning and reflection (agent learns what works across sequential dates, adjusting what it looks for).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from .. import config
from ..models import DateRecord, Person


# ------------------------------------------------------------- Pre-date Coaching

def add_coaching_note(person: Person, note: str) -> bool:
    clean = note.strip()
    if not clean:
        return False
    if clean not in person.coaching_notes:
        person.coaching_notes.append(clean)
        return True
    return False


def remove_coaching_note(person: Person, index: int) -> bool:
    if 0 <= index < len(person.coaching_notes):
        person.coaching_notes.pop(index)
        return True
    return False


# ------------------------------------------------------------- Post-date Feedback

class FeedbackDelta(BaseModel):
    summary: str = Field(description="Short summary of the adjustment")
    add_dealbreakers: list[str] = Field(default_factory=list)
    remove_dealbreakers: list[str] = Field(default_factory=list)
    add_needs: list[str] = Field(default_factory=list)
    remove_needs: list[str] = Field(default_factory=list)
    add_coaching: list[str] = Field(default_factory=list)
    adjust_lifestyle: dict[str, str] = Field(default_factory=dict)


def _heuristic_feedback_parser(feedback: str) -> FeedbackDelta:
    raw = feedback.strip()
    low = raw.lower()
    delta = FeedbackDelta(summary=raw)

    # 1. Negative / Dealbreaker indicators
    # Patterns: "hate X", "hates X", "don't like X", "no X", "can't stand X", "dealbreaker: X"
    neg_patterns = [
        r"(?:hate|hates|dislike|can\'?t stand|despise)\s+([a-zA-Z0-9\s\-]+?)(?:\.|\,|$|and\s)",
        r"(?:dealbreaker[:\s]+)([a-zA-Z0-9\s\-]+?)(?:\.|\,|$|and\s)",
        r"(?:never\s+want\s+to\s+deal\s+with|never\s+date\s+someone\s+who)\s+([a-zA-Z0-9\s\-]+?)(?:\.|\,|$)",
        r"(?:no\s+more\s+|don\'?t\s+bring\s+up\s+)([a-zA-Z0-9\s\-]+?)(?:\.|\,|$)",
    ]
    for pat in neg_patterns:
        matches = re.findall(pat, low)
        for m in matches:
            item = m.strip().strip(". ,")
            if item and len(item) > 2 and item not in ("me", "them", "it", "this"):
                # Clean up e.g. "clubs" -> "No clubs or partying" or item capitalized
                clean_db = f"No {item}" if not item.startswith("no ") else item.capitalize()
                delta.add_dealbreakers.append(clean_db)

    # 2. Positive / Need indicators
    # Patterns: "need someone who X", "want someone who X", "need X", "look for someone X", "love X"
    pos_patterns = [
        r"(?:need\s+someone\s+who\s+|needs?\s+someone\s+who\s+)([a-zA-Z0-9\s\-]+?)(?:\.|\,|$)",
        r"(?:want\s+someone\s+who\s+|wants?\s+someone\s+who\s+)([a-zA-Z0-9\s\-]+?)(?:\.|\,|$)",
        r"(?:look\s+for\s+someone\s+|look\s+for\s+more\s+of\s+)([a-zA-Z0-9\s\-]+?)(?:\.|\,|$)",
        r"(?:need\s+|i\s+need\s+)([a-zA-Z0-9\s\-]+?)(?:\.|\,|$|and\s)",
    ]
    for pat in pos_patterns:
        matches = re.findall(pat, low)
        for m in matches:
            item = m.strip().strip(". ,")
            if item and len(item) > 2 and item not in ("to", "a", "the", "me", "them", "it"):
                delta.add_needs.append(item.capitalize())

    # 3. Always add the human's feedback note to coaching so future dates directly remember it
    directive = raw
    if directive.lower().startswith("you got me wrong,"):
        directive = directive[len("you got me wrong,"):].strip()
    if directive and directive not in delta.add_coaching:
        delta.add_coaching.append(f"Feedback correction: {directive}")

    return delta


def parse_feedback(feedback_text: str, current_person: Person) -> FeedbackDelta:
    if config.llm_enabled():
        from . import llm
        try:
            a = current_person.analysis
            prompt = (
                f"You are updating a dating profile brief based on direct user feedback after a date or review.\n"
                f"User: {a.display_name if a else current_person.id}\n"
                f"Current Needs: {a.needs if a else []}\n"
                f"Current Dealbreakers: {a.dealbreakers if a else []}\n"
                f"Current Hobbies: {a.hobbies if a else []}\n\n"
                f"User feedback: \"{feedback_text}\"\n\n"
                f"Determine structured updates to the agent's brief. If the user says they hate something (e.g. clubs), "
                f"add it to dealbreakers and remove from hobbies if relevant. If they state a relationship need, add to needs."
            )
            return llm.structured("You parse dating agent user corrections into structured brief updates.",
                                  prompt, FeedbackDelta, max_tokens=600)
        except Exception:
            pass
    return _heuristic_feedback_parser(feedback_text)


def apply_feedback(person: Person, feedback_text: str, date_id: str | None = None) -> dict:
    delta = parse_feedback(feedback_text, person)
    changes = []

    if not person.analysis:
        return {"error": "Person profile not analyzed yet", "changes": []}

    a = person.analysis

    # Apply dealbreakers
    for db in delta.add_dealbreakers:
        if db not in a.dealbreakers:
            a.dealbreakers.append(db)
            changes.append(f"Added dealbreaker: {db}")
        # remove conflicting items from hobbies / interests
        lower_db = db.lower()
        a.hobbies = [h for h in a.hobbies if h.lower() not in lower_db]
        a.interests = [i for i in a.interests if i.lower() not in lower_db]

    for db in delta.remove_dealbreakers:
        if db in a.dealbreakers:
            a.dealbreakers.remove(db)
            changes.append(f"Removed dealbreaker: {db}")

    # Apply needs
    for nd in delta.add_needs:
        if nd not in a.needs:
            a.needs.insert(0, nd)
            changes.append(f"Added priority need: {nd}")

    for nd in delta.remove_needs:
        if nd in a.needs:
            a.needs.remove(nd)
            changes.append(f"Removed need: {nd}")

    # Apply coaching directives
    for c in delta.add_coaching:
        if c not in person.coaching_notes:
            person.coaching_notes.append(c)
            changes.append(f"Added coaching directive: {c}")

    if not changes:
        # Fallback note if no regex/LLM rule matched
        note = f"Noted: {feedback_text.strip()}"
        if note not in person.coaching_notes:
            person.coaching_notes.append(note)
            changes.append(f"Added coaching note: {note}")

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "date_id": date_id,
        "feedback": feedback_text.strip(),
        "changes": changes,
    }
    person.feedback_history.append(entry)
    return {"status": "ok", "changes": changes, "entry": entry}


# ------------------------------------------------------------- Cross-date Learning

def reflect_on_dates(person: Person, dates: list[DateRecord], pool: list[Person]) -> list[str]:
    """Agent analyzes all its dates so far and generates evolving insights on what works."""
    if not dates or not person.analysis:
        return person.dating_learnings

    by_id = {p.id: p for p in pool}
    learnings: list[str] = []

    # Partition dates into high-chemistry vs friction
    good_dates = []
    friction_dates = []
    for d in dates:
        other_id = d.b if d.a == person.id else d.a
        my_verdict = d.verdict_a if d.a == person.id else d.verdict_b
        other_person = by_id.get(other_id)
        other_name = other_person.analysis.display_name.split()[0] if other_person and other_person.analysis else other_id
        if my_verdict.score >= 6.0 and not my_verdict.dealbreaker_hit:
            good_dates.append((d, my_verdict, other_name))
        else:
            friction_dates.append((d, my_verdict, other_name))

    # Synthesis 1: High chemistry patterns
    if good_dates:
        best_d, best_v, best_name = max(good_dates, key=lambda x: x[1].score)
        venue_activity = best_d.venue_reason.lower().replace("both are into ", "").replace("both love ", "")
        learnings.append(
            f"Strongest chemistry emerged with {best_name} ({best_v.score:.1f}/10) over shared {venue_activity}; "
            f"agent prioritizes activities with real-world overlap."
        )

    # Synthesis 2: Friction & Dealbreaker calibration
    if friction_dates:
        worst_d, worst_v, worst_name = min(friction_dates, key=lambda x: x[1].score)
        if worst_v.dealbreaker_hit:
            db_reason = next((r for r in worst_v.reasons if "dealbreaker" in r.lower()), "lifestyle clash")
            learnings.append(
                f"Calibrated dealbreaker boundary after date with {worst_name}: {db_reason}. "
                f"Agent will probe boundaries earlier in conversations."
            )
        else:
            learnings.append(
                f"Identified energy/pace divergence with {worst_name}; "
                f"agent now looks for more aligned daily rhythm and communication style."
            )

    # Synthesis 3: Selectivity & Evolution across rounds
    n_dates = len(dates)
    if n_dates >= 3:
        avg_score = sum((d.verdict_a.score if d.a == person.id else d.verdict_b.score) for d in dates) / n_dates
        if avg_score > 6.0:
            learnings.append(
                f"Across {n_dates} dates, high mutual enthusiasm observed; agent is fine-tuning for long-term values alignment."
            )
        else:
            learnings.append(
                f"Across {n_dates} dates, agent has become significantly more selective on partner emotional availability."
            )

    person.dating_learnings = learnings
    return learnings
