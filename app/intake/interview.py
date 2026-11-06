"""AI Conversational Intake Interview: '3-Minute Coffee with Your Agent'.

Conducts structured intake interviews to capture authentic relationship dynamics:
- Sunday rhythm & daily energy pace
- Non-negotiable boundaries & dealbreakers
- Emotional communication under stress
- Latent personal aspirations and passions
- Ideal first date atmosphere

Synthesizes a grounded Analysis object with direct citations back to the user's quotes.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from ..models import Analysis, Evidence, InstagramData, LinkedInData, Person, SourceBundle

logger = logging.getLogger(__name__)

INTAKE_QUESTIONS = [
    {
        "id": "sunday_rhythm",
        "title": "Sunday Morning Rhythm",
        "question": "What does your ideal, uninterrupted Sunday look like?",
        "placeholder": "e.g. Quiet pour-over coffee, reading in morning light, a trail run, then parallel creative focus without social rush.",
        "category": "lifestyle",
    },
    {
        "id": "dealbreakers",
        "title": "Non-Negotiable Boundaries",
        "question": "What are 1 or 2 hard boundaries or non-negotiables for you in a relationship?",
        "placeholder": "e.g. Relocating abroad, emotional avoidance/stonewalling, smoking, workaholism without boundaries.",
        "category": "dealbreakers",
    },
    {
        "id": "communication",
        "title": "Emotional & Conflict Style",
        "question": "When you feel stressed or misunderstood, how do you prefer to communicate?",
        "placeholder": "e.g. I need 30 minutes of space to process, followed by direct, calm, non-defensive check-ins.",
        "category": "communication",
    },
    {
        "id": "latent_passions",
        "title": "Hidden Longings & Dreams",
        "question": "Outside of work, what is something you're secretly building, dreaming of, or longing to explore?",
        "placeholder": "e.g. Building an off-grid mountain wildlife sanctuary, learning ceramic pottery, writing a graphic novel.",
        "category": "aspirations",
    },
    {
        "id": "ideal_date",
        "title": "First Date Atmosphere",
        "question": "If your agent could plan the perfect first date venue and vibe for you, what would it be?",
        "placeholder": "e.g. A cozy, quiet vinyl café with corner seating where we can actually hear each other talk.",
        "category": "dating",
    },
]


def extract_keywords_from_text(text: str, default: list[str]) -> list[str]:
    """Extract clean comma- or space-separated concepts from text."""
    if not text:
        return default
    # Split by commas or semicolons
    chunks = re.split(r"[,;\n]+", text)
    cleaned = [c.strip(" -•*") for c in chunks if len(c.strip(" -•*")) > 2]
    return cleaned[:6] if cleaned else default


def infer_lifestyle_pace(sunday_text: str) -> str:
    """Infer lifestyle pacing from Sunday morning response."""
    lower = sunday_text.lower()
    if any(w in lower for w in ["quiet", "slow", "peaceful", "pour-over", "reading", "gentle", "meditation", "sleep"]):
        return "Slow intentional living"
    if any(w in lower for w in ["run", "hike", "workout", "early", "climb", "boulder", "cycling", "market"]):
        return "Early morning adventurer"
    if any(w in lower for w in ["build", "startup", "busy", "code", "fast", "growth", "project"]):
        return "Fast-paced creator"
    return "Balanced rhythm"


def synthesize_interview_persona(
    display_name: str,
    one_liner: str,
    answers: dict[str, str],
    pid: Optional[str] = None,
) -> Person:
    """Synthesize complete Person model from interactive interview answers."""
    import secrets

    person_id = pid or f"intake-{secrets.token_hex(4)}"
    clean_name = display_name.strip() or "Anonymous Dater"
    clean_headline = one_liner.strip() or "AMORA Intake Participant"

    sunday = answers.get("sunday_rhythm", "").strip()
    dealbreakers_raw = answers.get("dealbreakers", "").strip()
    communication = answers.get("communication", "").strip()
    passions = answers.get("latent_passions", "").strip()
    ideal_date = answers.get("ideal_date", "").strip() or "A quiet spot with authentic conversation"

    # Derive lifestyle pace & hobbies
    pace = infer_lifestyle_pace(sunday)
    hobbies = extract_keywords_from_text(sunday, default=["Reading", "Pour-over coffee", "Trail walks"])
    if passions:
        hobbies.extend(extract_keywords_from_text(passions, default=[])[:2])

    dealbreakers = extract_keywords_from_text(dealbreakers_raw, default=["Disrespecting boundaries", "Emotional stonewalling"])

    # Build evidence receipts directly citing the human's spoken words
    evidence_items = []
    if sunday:
        evidence_items.append(
            Evidence(
                claim=f"Lifestyle Pace: {pace}",
                source="linkedin",
                snippet=f"Intake interview: '{sunday[:120]}'",
            )
        )
    if dealbreakers:
        evidence_items.append(
            Evidence(
                claim=f"Boundary: {dealbreakers[0]}",
                source="instagram",
                snippet=f"Intake interview: '{dealbreakers_raw[:120]}'",
            )
        )
    if communication:
        evidence_items.append(
            Evidence(
                claim="Communication Preference",
                source="linkedin",
                snippet=f"Intake interview: '{communication[:120]}'",
            )
        )

    # Values inferred from depth of answers
    values = ["Honesty", "Emotional Presence", "Intentional Living"]
    if "ambition" in passions.lower() or "startup" in passions.lower() or "build" in passions.lower():
        values.append("Ambition & Craft")
    if "family" in sunday.lower() or "home" in sunday.lower():
        values.append("Family Warmth")

    analysis = Analysis(
        display_name=clean_name,
        one_liner=clean_headline,
        summary=f"{clean_name} values {', '.join(values[:2])} with a {pace.lower()}. Outside of work: {passions[:80] if passions else 'creative and outdoor curiosity'}.",
        needs=[
            f"A partner who aligns with {pace.lower()}",
            "Emotional safety and non-defensive communication",
            f"Shared passion for {hobbies[0] if hobbies else 'growth'}",
        ],
        hobbies=hobbies[:5],
        interests=[hobbies[0] if hobbies else "Meaningful dialogue", "Deep focus", "Cultural curiosity"],
        values=values,
        personality=["Thoughtful", "Reflective", "Grounded"],
        lifestyle={"pace": pace, "social_energy": "Selective & Deep"},
        communication_style=communication if communication else "Direct, calm, and thoughtful",
        green_flags=["Clear self-awareness", "Respect for quiet spaces", "Emotional vulnerability"],
        dealbreakers=dealbreakers,
        ideal_date=ideal_date,
        conversation_starters=[
            f"What does your favorite Sunday look like?",
            f"Tell me about what you're creating or longing to explore lately.",
        ],
        evidence=evidence_items,
        confidence=0.95,
        engine_used="ai_intake_interview",
    )

    li_url = f"https://example.com/in/{person_id}"
    ig_url = f"https://example.com/ig/{person_id}"

    sources = SourceBundle(
        linkedin=LinkedInData(url=li_url, full_name=clean_name, headline=clean_headline, about=passions or clean_headline),
        instagram=InstagramData(url=ig_url, username=person_id, full_name=clean_name, bio=sunday or clean_headline),
    )

    coaching = [
        f"Remember my core boundary: {dealbreakers[0]}." if dealbreakers else "Probe authentic life alignment.",
        f"Ask about their lifestyle pacing and if they enjoy {pace.lower()}.",
    ]

    return Person(
        id=person_id,
        linkedin_url=li_url,
        instagram_url=ig_url,
        consent=True,
        status="analyzed",
        analysis=analysis,
        sources=sources,
        coaching_notes=coaching,
    )
