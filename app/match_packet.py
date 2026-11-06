"""Match Packet Executive Dossier Generator.

Compiles a comprehensive, printable executive dossier for mutual matches:
1. Compatibility breakdown & harmonic mutual score.
2. What the autonomous agents discovered about each other.
3. The 'First Fight' resilience assessment under stress.
4. The agreed second-date proposal (venue, activity, time, budget tier).
5. Personalized drafted introductory message (ready to send).
6. Factuality & grounding audit receipts.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import HTTPException

from . import store
from .models import DateRecord, Person

logger = logging.getLogger(__name__)


def build_match_packet_data(did: str) -> dict[str, Any]:
    """Compile comprehensive match dossier for date ID."""
    d = store.get_date(did)
    if not d:
        raise HTTPException(404, "Date not found")

    pa = store.get_person(d.a)
    pb = store.get_person(d.b)
    if not pa or not pb:
        raise HTTPException(400, "Date participants not found")

    name_a = pa.analysis.display_name if pa.analysis else d.a
    name_b = pb.analysis.display_name if pb.analysis else d.b
    first_a = name_a.split()[0]
    first_b = name_b.split()[0]

    both_yes = bool(d.verdict_a.second_date and d.verdict_b.second_date)

    # Ensure second date plan, first fight stress test, and audit are generated if mutual yes
    if both_yes and not d.second_date_plan:
        try:
            from .agents import planner
            planner.plan_second_date(d, pa, pb)
            store.save_date(d)
        except Exception as e:
            logger.info("Second date plan generation skipped: %s", e)

    if both_yes and not d.first_fight:
        try:
            from .agents import stress
            stress.simulate_first_fight(d, pa, pb)
            store.save_date(d)
        except Exception as e:
            logger.info("First fight simulation skipped: %s", e)

    if not d.honesty_audit:
        try:
            from .agents import judge
            judge.audit_date(d, pa, pb)
            store.save_date(d)
        except Exception as e:
            logger.info("Honesty audit skipped: %s", e)

    # Reload date to get generated plans
    d = store.get_date(did) or d

    # Shared tags & values
    values_a = set(pa.analysis.values if pa.analysis else [])
    values_b = set(pb.analysis.values if pb.analysis else [])
    shared_values = list(values_a.intersection(values_b))

    hobbies_a = set(pa.analysis.hobbies if pa.analysis else [])
    hobbies_b = set(pb.analysis.hobbies if pb.analysis else [])
    shared_hobbies = list(hobbies_a.intersection(hobbies_b))

    return {
        "date_id": d.id,
        "both_yes": both_yes,
        "mutual_score": d.mutual,
        "venue": d.venue,
        "venue_reason": d.venue_reason,
        "person_a": {
            "id": pa.id,
            "full_name": name_a,
            "first_name": first_a,
            "one_liner": pa.analysis.one_liner if pa.analysis else "",
            "pace": (pa.analysis.lifestyle or {}).get("pace", "Balanced") if pa.analysis else "Balanced",
            "score": d.verdict_a.score,
            "chemistry": d.verdict_a.chemistry,
            "needs_met": d.verdict_a.needs_met,
            "values_alignment": d.verdict_a.values_alignment,
            "second_date": d.verdict_a.second_date,
            "report_to_human": d.verdict_a.report_to_human,
            "learned_about_other": d.verdict_a.learned_about_other,
            "coaching_directives": pa.coaching_notes,
            "instagram_url": pa.instagram_url,
            "linkedin_url": pa.linkedin_url,
        },
        "person_b": {
            "id": pb.id,
            "full_name": name_b,
            "first_name": first_b,
            "one_liner": pb.analysis.one_liner if pb.analysis else "",
            "pace": (pb.analysis.lifestyle or {}).get("pace", "Balanced") if pb.analysis else "Balanced",
            "score": d.verdict_b.score,
            "chemistry": d.verdict_b.chemistry,
            "needs_met": d.verdict_b.needs_met,
            "values_alignment": d.verdict_b.values_alignment,
            "second_date": d.verdict_b.second_date,
            "report_to_human": d.verdict_b.report_to_human,
            "learned_about_other": d.verdict_b.learned_about_other,
            "coaching_directives": pb.coaching_notes,
            "instagram_url": pb.instagram_url,
            "linkedin_url": pb.linkedin_url,
        },
        "shared_values": shared_values,
        "shared_hobbies": shared_hobbies,
        "second_date_plan": d.second_date_plan.model_dump() if d.second_date_plan else None,
        "first_fight": d.first_fight.model_dump() if d.first_fight else None,
        "honesty_audit": d.honesty_audit.model_dump() if d.honesty_audit else None,
        "whispers_count": len(d.whispers),
    }
