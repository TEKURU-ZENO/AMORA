"""Synthetic Ground Truth benchmark personas and planted couples for evaluation.

Provides 3 rigorously controlled cohorts:
1. True Compatible (Ideal Matches): complementary needs, strong shared values/hobbies, zero dealbreakers.
2. Dealbreaker Clashes (True Negatives): fundamental non-negotiable dealbreaker collision.
3. Superficial Traps (Trick Pairs): high surface keyword overlap (coffee, travel) masking emotional/relational incompatibility.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..models import Analysis, Evidence, InstagramData, InstagramPost, LinkedInData, LinkedInExperience, Person, SourceBundle


@dataclass
class GroundTruthCouple:
    person_a_id: str
    person_b_id: str
    category: Literal["compatible", "dealbreaker_clash", "superficial_trap"]
    expected_relevant: bool
    expected_second_date: bool
    target_score_min: float
    target_score_max: float
    expected_rank_max: int  # e.g., 3 means must be in top 3
    rationale: str


def _build_test_bundle(
    pid: str,
    name: str,
    headline: str,
    summary: str,
    needs: list[str],
    hobbies: list[str],
    interests: list[str],
    values: list[str],
    personality: list[str],
    dealbreakers: list[str],
    communication_style: str,
    lifestyle_pace: str,
    social_energy: str,
) -> Person:
    """Helper to construct an evaluated Person with Analysis and Evidence."""
    li_url = f"https://example.com/linkedin/{pid}"
    ig_url = f"https://example.com/instagram/{pid}"
    
    analysis = Analysis(
        display_name=name,
        one_liner=headline,
        summary=summary,
        needs=needs,
        hobbies=hobbies,
        interests=interests,
        values=values,
        personality=personality,
        lifestyle={"pace": lifestyle_pace, "social_energy": social_energy},
        communication_style=communication_style,
        green_flags=["Clear communicator", "Self-aware", "Consistent routines"],
        dealbreakers=dealbreakers,
        ideal_date="Casual coffee followed by a walk or shared activity",
        conversation_starters=[f"How did you get into {hobbies[0]}?" if hobbies else "What's your weekend vibe?"],
        evidence=[
            Evidence(claim=f"Enjoys {hobbies[0]}", source="instagram", snippet=f"Weekend {hobbies[0]} session") if hobbies else Evidence(claim="Active professional", source="linkedin", snippet="Works in tech"),
            Evidence(claim=f"Values {values[0]}", source="linkedin", snippet=f"Advocates for {values[0]} in community") if values else Evidence(claim="Thoughtful", source="instagram", snippet="Quiet reflections"),
        ],
        confidence=0.92,
        engine_used="benchmark_synth",
    )

    li_data = LinkedInData(
        url=li_url,
        full_name=name,
        headline=headline,
        about=summary,
        experience=[LinkedInExperience(title=headline.split("at")[0].strip(), company="Eval Corp", duration="2022 - Present", description="Building software")],
    )
    ig_data = InstagramData(
        url=ig_url,
        username=pid,
        full_name=name,
        bio=f"{headline} · {', '.join(hobbies[:2])}",
        posts=[InstagramPost(caption=f"Enjoying {hobbies[0]} this weekend #life", hashtags=[hobbies[0].lower()]) if hobbies else InstagramPost(caption="City moments", hashtags=["city"])],
    )

    return Person(
        id=pid,
        linkedin_url=li_url,
        instagram_url=ig_url,
        consent=True,
        synthetic=True,
        analysis=analysis,
        sources=SourceBundle(linkedin=li_data, instagram=ig_data),
        status="analyzed",
    )


def generate_benchmark_testbed() -> tuple[list[Person], list[GroundTruthCouple]]:
    """Build the synthetic evaluation cohort and ground truth evaluation expectations."""
    people: list[Person] = []

    # 1. Compatible Pair 1: Ananya (Bouldering/Books) & Kabir (Climbing/Literature)
    p_ananya = _build_test_bundle(
        pid="eval-ananya",
        name="Ananya Rao",
        headline="Climate Researcher at EcoLabs",
        summary="Passionate about sustainability and quiet weekend adventures.",
        needs=["An emotionally present partner who loves outdoor adventure"],
        hobbies=["Bouldering", "Reading", "Trail Hiking"],
        interests=["Climate policy", "Indie literature", "Espresso"],
        values=["Family and closeness", "Environmental care", "Honesty"],
        personality=["Thoughtful", "Grounded", "Adventurous"],
        dealbreakers=["Emotional unavailability", "Smoking"],
        communication_style="Warm, direct, reflective",
        lifestyle_pace="Balanced with early mornings",
        social_energy="Introverted with close circle",
    )
    p_kabir = _build_test_bundle(
        pid="eval-kabir",
        name="Kabir Menon",
        headline="Environmental Economist at GreenTech",
        summary="Economics researcher who spends weekends on climbing crags and reading philosophy.",
        needs=["A thoughtful partner who shares outdoor curiosity and values calm reflection"],
        hobbies=["Bouldering", "Reading", "Photography"],
        interests=["Environmental science", "Philosophy", "Filter coffee"],
        values=["Family and closeness", "Curiosity", "Honesty"],
        personality=["Grounded", "Calm", "Reflective"],
        dealbreakers=["Excessive cynicism", "Smoking"],
        communication_style="Warm, thoughtful, active listener",
        lifestyle_pace="Balanced with early mornings",
        social_energy="Introverted with close circle",
    )

    # 2. Compatible Pair 2: Vikram (Founder/Trekker) & Meera (Designer/Runner)
    p_vikram = _build_test_bundle(
        pid="eval-vikram",
        name="Vikram Pillai",
        headline="Founder at NextCloud",
        summary="Tech builder who prioritizes family values and weekend mountain trails.",
        needs=["An ambitious, creative partner with grounded family values"],
        hobbies=["Trail Running", "Cooking", "Trekking"],
        interests=["Product design", "Italian cuisine", "Startups"],
        values=["Family and closeness", "Ambition with humility", "Health"],
        personality=["Dynamic", "Empathetic", "Driven"],
        dealbreakers=["Secretive behavior", "Disrespect towards family"],
        communication_style="Direct, collaborative, witty",
        lifestyle_pace="Active and purposeful",
        social_energy="Ambivert",
    )
    p_meera = _build_test_bundle(
        pid="eval-meera",
        name="Meera Kapoor",
        headline="Lead Product Designer at Studio Figma",
        summary="Designing thoughtful experiences, passionate about long runs and weekend sourdough.",
        needs=["A supportive partner who understands creative dedication and shares warmth"],
        hobbies=["Trail Running", "Cooking", "Ceramics"],
        interests=["Product design", "Culinary arts", "Art history"],
        values=["Family and closeness", "Creativity", "Health"],
        personality=["Creative", "Warm", "Dedicated"],
        dealbreakers=["Disrespect towards family", "Arrogance"],
        communication_style="Articulate, empathetic, open",
        lifestyle_pace="Active and purposeful",
        social_energy="Ambivert",
    )

    # 3. Compatible Pair 3: Tara (Film/Music) & Neel (Photography/Cinema)
    p_tara = _build_test_bundle(
        pid="eval-tara",
        name="Tara Nair",
        headline="Documentary Editor at IndieWave",
        summary="Storyteller obsessed with 35mm film, vinyl records, and long conversations.",
        needs=["A creative soul who appreciates nuance and quiet connection"],
        hobbies=["Film Photography", "Vinyl Collecting", "Cinema"],
        interests=["World cinema", "Acoustic folk", "Architecture"],
        values=["Authenticity", "Kindness", "Patience"],
        personality=["Observant", "Gentle", "Artistic"],
        dealbreakers=["Aggressive communication", "Flashy materialism"],
        communication_style="Soft-spoken, deeply observant",
        lifestyle_pace="Slow living",
        social_energy="Selective introvert",
    )
    p_neel = _build_test_bundle(
        pid="eval-neel",
        name="Neel Joshi",
        headline="Cinematographer & Visual Artist",
        summary="Visual explorer documenting city architecture and independent musicians.",
        needs=["An observant partner who values authentic moments and quiet warmth"],
        hobbies=["Film Photography", "Cinema", "Jazz"],
        interests=["Visual storytelling", "Old cinema", "Coffee brewing"],
        values=["Authenticity", "Kindness", "Creative integrity"],
        personality=["Gentle", "Attentive", "Artistic"],
        dealbreakers=["Aggressive communication", "Superficiality"],
        communication_style="Attentive, patient, perceptive",
        lifestyle_pace="Slow living",
        social_energy="Selective introvert",
    )

    # 4. Dealbreaker Clash 1: Rohan (Quiet Homebody) vs Zoya (Clubbing DJ)
    p_rohan = _build_test_bundle(
        pid="eval-rohan",
        name="Rohan Shah",
        headline="Quant Researcher at AlphaFund",
        summary="Strict daily routine, early sleeper, cherishes total peace on weekends.",
        needs=["A calm partner who thrives in quiet home environments"],
        hobbies=["Chess", "Math Puzzles", "Classical Piano"],
        interests=["Algorithmic trading", "Acoustics", "Tea"],
        values=["Discipline", "Peace and quiet", "Frugality"],
        personality=["Structured", "Introspective", "Quiet"],
        dealbreakers=["Nightclubbing, loud nightlife parties", "Heavy alcohol"],
        communication_style="Precise, literal, quiet",
        lifestyle_pace="Strict, predictable 9pm bedtime",
        social_energy="Deep introvert, avoids clubs",
    )
    p_zoya = _build_test_bundle(
        pid="eval-zoya",
        name="Zoya Mirza",
        headline="DJ & Nightlife Event Producer at Neon Nights",
        summary="Living at full volume! Club nights 4 days a week, hosting late-night rooftop parties.",
        needs=["A high-energy partner who loves partying until 4am and dancing"],
        hobbies=["Nightclubbing, loud nightlife parties", "Electronic Music", "Festival Hopping"],
        interests=["Techno", "Mixology", "Fashion"],
        values=["Spontaneity", "Social excitement", "Freedom"],
        personality=["Extroverted", "High-energy", "Nocturnal"],
        dealbreakers=["Rigid bedtimes", "Disliking electronic music"],
        communication_style="Loud, expressive, spontaneous",
        lifestyle_pace="Nocturnal, active until 5am",
        social_energy="Extreme extrovert",
    )

    # 5. Dealbreaker Clash 2: Arjun (Anchored Local) vs Sana (Perpetual Traveler)
    p_arjun = _build_test_bundle(
        pid="eval-arjun",
        name="Arjun Reddy",
        headline="Civil Engineer & City Planner",
        summary="Dedicated to local city infrastructure, deeply rooted in hometown community.",
        needs=["A grounded partner permanently settled in the local city"],
        hobbies=["Gardening", "Woodworking", "Local History"],
        interests=["Urban planning", "Historical maps", "Carpentry"],
        values=["Roots and stability", "Community", "Local connection"],
        personality=["Steadfast", "Traditional", "Dependable"],
        dealbreakers=["Frequent relocation or traveling >50% of the year", "Unsettled lifestyle"],
        communication_style="Steady, clear, practical",
        lifestyle_pace="Grounded local routine",
        social_energy="Community oriented",
    )
    p_sana = _build_test_bundle(
        pid="eval-sana",
        name="Sana Das",
        headline="International Wildlife Documentarian",
        summary="Living out of a backpack across South America and Africa 9 months a year.",
        needs=["A nomad partner with zero roots who will travel the world constantly"],
        hobbies=["Frequent relocation or traveling >50% of the year", "Backpacking", "Scuba"],
        interests=["Wildlife conservation", "Nomadic living", "Survivalism"],
        values=["Total wanderlust", "Freedom", "Non-attachment"],
        personality=["Adventurous", "Nomadic", "Restless"],
        dealbreakers=["Wanting to settle down in one city", "Domestic routines"],
        communication_style="Fast-paced, global, detached",
        lifestyle_pace="Perpetual travel, changing cities weekly",
        social_energy="Nomad",
    )

    # 6. Superficial Trap: Kiran (Emotional Seeker) vs Ishita (Emotionally Guarded Banter)
    # Both share surface keywords: "Coffee", "Travel", "Reading"
    # But Kiran's core need is emotional vulnerability; Ishita triggers Kiran's dealbreaker on emotional avoidance!
    p_kiran = _build_test_bundle(
        pid="eval-kiran",
        name="Kiran Sen",
        headline="Writer & Narrative Essayist",
        summary="Coffee lover and traveler who seeks deep vulnerability, emotional presence, and heart-to-heart talks.",
        needs=["Radical emotional vulnerability and discussing deep feelings"],
        hobbies=["Coffee", "Travel", "Reading"],
        interests=["Memoirs", "Psychology", "Poetry"],
        values=["Emotional honesty", "Vulnerability", "Deep empathy"],
        personality=["Empathetic", "Introspective", "Heartfelt"],
        dealbreakers=["Emotionally unavailable or evasive banter", "Mocking feelings"],
        communication_style="Vulnerable, soulful, expressive",
        lifestyle_pace="Reflective and intentional",
        social_energy="Selective depth",
    )
    p_ishita = _build_test_bundle(
        pid="eval-ishita",
        name="Ishita Bose",
        headline="Corporate Derivatives Trader",
        summary="Coffee enthusiast and frequent weekend traveler who avoids all emotional discussions.",
        needs=["Someone who keeps things 100% light, sarcastic, and never talks about feelings"],
        hobbies=["Coffee", "Travel", "Reading"],
        interests=["Market charts", "Espresso gear", "Airport lounges"],
        values=["Detachment", "Pragmatism", "Thick skin"],
        personality=["Sarcastic", "Stoic", "Guarded"],
        dealbreakers=["Asking about feelings", "Emotional intimacy early on"],
        communication_style="Emotionally unavailable or evasive banter",
        lifestyle_pace="Corporate rush",
        social_energy="Networking focus",
    )

    people = [
        p_ananya, p_kabir, p_vikram, p_meera, p_tara, p_neel,
        p_rohan, p_zoya, p_arjun, p_sana, p_kiran, p_ishita,
    ]

    couples = [
        GroundTruthCouple(
            person_a_id="eval-ananya",
            person_b_id="eval-kabir",
            category="compatible",
            expected_relevant=True,
            expected_second_date=True,
            target_score_min=6.5,
            target_score_max=9.8,
            expected_rank_max=2,
            rationale="Shared bouldering, literature, early morning pace, and mutual need for grounded warmth.",
        ),
        GroundTruthCouple(
            person_a_id="eval-vikram",
            person_b_id="eval-meera",
            category="compatible",
            expected_relevant=True,
            expected_second_date=True,
            target_score_min=6.5,
            target_score_max=9.8,
            expected_rank_max=2,
            rationale="Shared trail running, creative dedication, family values, and complementary ambition.",
        ),
        GroundTruthCouple(
            person_a_id="eval-tara",
            person_b_id="eval-neel",
            category="compatible",
            expected_relevant=True,
            expected_second_date=True,
            target_score_min=6.5,
            target_score_max=9.5,
            expected_rank_max=2,
            rationale="Shared 35mm film photography, world cinema, and quiet slow-living communication style.",
        ),
        GroundTruthCouple(
            person_a_id="eval-rohan",
            person_b_id="eval-zoya",
            category="dealbreaker_clash",
            expected_relevant=False,
            expected_second_date=False,
            target_score_min=0.0,
            target_score_max=4.5,
            expected_rank_max=11,
            rationale="Severe dealbreaker clash: quiet quant with 9pm bedtime vs nightclub producer partying till 5am.",
        ),
        GroundTruthCouple(
            person_a_id="eval-arjun",
            person_b_id="eval-sana",
            category="dealbreaker_clash",
            expected_relevant=False,
            expected_second_date=False,
            target_score_min=0.0,
            target_score_max=4.5,
            expected_rank_max=11,
            rationale="Severe dealbreaker clash: rooted local urban planner vs perpetual nomad traveling 9 months/year.",
        ),
        GroundTruthCouple(
            person_a_id="eval-kiran",
            person_b_id="eval-ishita",
            category="superficial_trap",
            expected_relevant=False,
            expected_second_date=False,
            target_score_min=0.0,
            target_score_max=6.0,
            expected_rank_max=11,
            rationale="Superficial trap: share 'coffee/travel/reading' on paper, but Ishita hits Kiran's dealbreaker on emotional avoidance.",
        ),
    ]

    return people, couples
