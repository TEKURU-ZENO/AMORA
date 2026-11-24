"""AMORA Psychological & Behavioral Archetype Profiling Engine.

Replaces web scraping with deep psychological and behavioral analysis:
- Stereotype & Relational Archetypes (12 canonical relational identities)
- Attachment Dynamics (Secure, Anxious, Dismissive-Avoidant, Fearful-Avoidant)
- Conflict Resolution & Stress Pacing (Gottman taxonomy & emotional processing)
- Life Architecture (Sunday rhythm, geographic anchors, family vision, social battery)
- Work Ethos & Ambition (startup drive vs 5 PM boundaries, financial philosophy)
- Future Visions & Secret Dreams (5-year horizons and creative longings)
- Hard Relational Dealbreakers & Boundaries

Enables dating agents to authentically match the required persona's emotional cadence,
conversational tempo, conflict defenses, and core relational needs.
"""
from __future__ import annotations

import logging
import re
import secrets
from typing import Any, Optional

from ..models import (
    Analysis,
    Evidence,
    InstagramData,
    LinkedInData,
    Person,
    SourceBundle,
)

logger = logging.getLogger(__name__)

# =====================================================================
# 1. The 12 Canonical Relational Archetypes & Stereotypes
# =====================================================================

ARCHETYPES: dict[str, dict[str, Any]] = {
    "contemplative_craftsman": {
        "id": "contemplative_craftsman",
        "name": "The Contemplative Craftsman",
        "tagline": "Quiet mastery, tactile or intellectual flow, comfortable silence",
        "traits": [
            "Values deep focus over social chatter",
            "Flourishes in parallel creative play",
            "Slow, deliberate conversational pacing",
            "Exhausted by performative socializing",
        ],
        "dating_strengths": "Gentle presence, attentive listening, unhurried authenticity",
        "vulnerabilities": "Feels overwhelmed by loud fast-talkers or pressured social calendars",
        "synergistic_archetypes": ["empathic_healer", "grounded_sanctuary", "cozy_domesticist"],
        "clashing_archetypes": ["high_octane_catalyst", "playful_maverick"],
        "keywords": ["craft", "wood", "audio", "code", "book", "silence", "parallel", "quiet", "tactile", "slow", "focus", "study", "cello", "piano", "reading"],
    },
    "visionary_builder": {
        "id": "visionary_builder",
        "name": "The Visionary Builder",
        "tagline": "Relentless creator, high mission drive, fast-moving ambition",
        "traits": [
            "Obsessed with building ideas into reality",
            "High daily velocity and bold risk appetite",
            "Seeks an equally ambitious partner or grounded anchor",
            "Suffocated by bureaucratic complacency or small thinking",
        ],
        "dating_strengths": "Infectious energy, strategic depth, unwavering support for partner's dreams",
        "vulnerabilities": "Can slip into workaholism; struggles to switch off without a boundary",
        "synergistic_archetypes": ["high_velocity_strategist", "grounded_sanctuary", "visionary_builder"],
        "clashing_archetypes": ["intentional_minimalist", "cozy_domesticist"],
        "keywords": ["startup", "build", "founder", "mission", "vision", "tech", "scale", "create", "product", "growth", "accelerate", "lead"],
    },
    "grounded_sanctuary": {
        "id": "grounded_sanctuary",
        "name": "The Grounded Sanctuary",
        "tagline": "Domestic warmth, rooted family values, community anchor",
        "traits": [
            "Permanently rooted in community or local caregiving",
            "Prioritizes emotional security, children, and long-term stability",
            "Warm domestic host who makes a house feel like a home",
            "Non-negotiable resistance to perpetual relocation",
        ],
        "dating_strengths": "Unshakeable loyalty, comforting warmth, steady emotional rock",
        "vulnerabilities": "Clashes with digital nomads or people who treat cities as temporary waypoints",
        "synergistic_archetypes": ["contemplative_craftsman", "cozy_domesticist", "visionary_builder"],
        "clashing_archetypes": ["mindful_nomad"],
        "keywords": ["root", "anchor", "family", "kids", "children", "home", "caregiver", "stable", "settled", "local", "community", "garden", "hometown"],
    },
    "mindful_nomad": {
        "id": "mindful_nomad",
        "name": "The Mindful Nomad",
        "tagline": "Geographic freedom, spontaneous exploration, experiential minimalism",
        "traits": [
            "Treats the world as an unfolding classroom",
            "Low attachment to material possessions; values suitcase mobility",
            "Thrives on unfamiliar cultures, languages, and spontaneous plans",
            "Suffocated by rigid suburban routines or 10-year mortgages",
        ],
        "dating_strengths": "Limitless curiosity, adventurous spark, adaptability in unfamiliar terrain",
        "vulnerabilities": "Resists premature roots; triggers abandonment fears in anxious partners",
        "synergistic_archetypes": ["holistic_seeker", "playful_maverick", "mindful_nomad"],
        "clashing_archetypes": ["grounded_sanctuary", "cozy_domesticist"],
        "keywords": ["nomad", "travel", "backpack", "relocate", "abroad", "tokyo", "explore", "spontaneous", "world", "remote", "flexible", "flight"],
    },
    "high_velocity_strategist": {
        "id": "high_velocity_strategist",
        "name": "The High-Velocity Strategist",
        "tagline": "Incisive intellect, corporate or legal powerhouse, high candor",
        "traits": [
            "Operates with sharp mental clarity and strategic precision",
            "Enjoys vigorous intellectual debate and witty sparring",
            "High professional standards; values competence and directness",
            "Guarded with early emotional disclosures; requires earned trust",
        ],
        "dating_strengths": "Unrivaled problem-solving, fierce advocacy, honest transparency",
        "vulnerabilities": "Can inadvertently turn a dinner date into a cross-examination or interview",
        "synergistic_archetypes": ["visionary_builder", "contemplative_craftsman", "sensual_epicurean"],
        "clashing_archetypes": ["empathic_healer", "playful_maverick"],
        "keywords": ["strategy", "law", "finance", "litigation", "analyst", "debate", "direct", "candor", "efficient", "intellect", "clarity", "rigor"],
    },
    "empathic_healer": {
        "id": "empathic_healer",
        "name": "The Empathic Healer",
        "tagline": "Soulful creativity, radical emotional honesty, deep intuition",
        "traits": [
            "High emotional intelligence and sensitivity to unspoken atmospheres",
            "Craves heart-to-heart vulnerability; allergic to polite facade",
            "Dedicated to healing arts, psychology, storytelling, or therapy",
            "Deeply wounded by sarcasm, emotional stonewalling, or mockery",
        ],
        "dating_strengths": "Profound psychological safety, heartfelt intimacy, emotional attunement",
        "vulnerabilities": "Absorbs other people's stress; easily flooded by harsh confrontation",
        "synergistic_archetypes": ["contemplative_craftsman", "holistic_seeker", "grounded_sanctuary"],
        "clashing_archetypes": ["high_velocity_strategist", "playful_maverick"],
        "keywords": ["empathy", "soul", "heal", "therapy", "feeling", "vulnerable", "honest", "heart", "sensitive", "psychology", "memoir", "poetry"],
    },
    "cozy_domesticist": {
        "id": "cozy_domesticist",
        "name": "The Cozy Domesticist",
        "tagline": "Homebody sanctuary, culinary exploration, slow peaceful rituals",
        "traits": [
            "Home is a sacred haven of comfort, good food, and calm music",
            "Loves hosting small dinner parties, board games, or cooking together",
            "Social battery drains after 90 minutes in loud crowds",
            "Overwhelmed by high-frequency nightlife or clubbing schedules",
        ],
        "dating_strengths": "Incredible culinary companionship, cozy domestic peace, grounding presence",
        "vulnerabilities": "Can get stuck in a protective cocoon; needs gentle encouragement to venture out",
        "synergistic_archetypes": ["grounded_sanctuary", "contemplative_craftsman", "intentional_minimalist"],
        "clashing_archetypes": ["high_octane_catalyst", "mindful_nomad"],
        "keywords": ["homebody", "cook", "bake", "recipe", "sourdough", "board game", "cozy", "blanket", "tea", "domestic", "quiet night", "nest"],
    },
    "high_octane_catalyst": {
        "id": "high_octane_catalyst",
        "name": "The High-Octane Catalyst",
        "tagline": "Life of the room, community curator, extroverted spark",
        "traits": [
            "Energized by loud rooms, festivals, mixers, and large circles",
            "Effortless conversational improviser who brings people together",
            "Thrives on full weekly calendars and evening social velocity",
            "Feels restless and lonely with prolonged domestic isolation",
        ],
        "dating_strengths": "Magnetic charisma, boundless enthusiasm, introduces partner to vast worlds",
        "vulnerabilities": "Struggles with slow, silent downtime; may neglect partner's low social battery",
        "synergistic_archetypes": ["playful_maverick", "sensual_epicurean", "visionary_builder"],
        "clashing_archetypes": ["cozy_domesticist", "contemplative_craftsman"],
        "keywords": ["party", "nightlife", "dj", "festival", "mixer", "event", "extrovert", "crowd", "social", "energy", "catalyst", "network", "club"],
    },
    "intentional_minimalist": {
        "id": "intentional_minimalist",
        "name": "The Intentional Minimalist (FIRE)",
        "tagline": "Conscious consumption, financial independence, sustainable living",
        "traits": [
            "Pursues Financial Independence / Retire Early (FIRE) and simple living",
            "Values experiences, repair culture, and time freedom over luxury goods",
            "Anti-consumerist philosophy; conscious of ecological footprint",
            "Deep value clash with conspicuous consumption or status signaling",
        ],
        "dating_strengths": "Total financial clarity, resourcefulness, intentional alignment of time",
        "vulnerabilities": "Can come across as rigid around dining out or travel spending",
        "synergistic_archetypes": ["contemplative_craftsman", "holistic_seeker", "cozy_domesticist"],
        "clashing_archetypes": ["sensual_epicurean", "visionary_builder"],
        "keywords": ["frugal", "fire", "minimalism", "save", "invest", "sustainable", "repair", "thrift", "eco", "bicycle", "budget", "anti-consumerist"],
    },
    "sensual_epicurean": {
        "id": "sensual_epicurean",
        "name": "The Sensual Epicurean",
        "tagline": "Fine gastronomy, aesthetic beauty, curated sensory experiences",
        "traits": [
            "Views life through taste, music, interior design, and visual elegance",
            "Loves natural wine, specialty coffees, Michelin gastronomy, and boutique stays",
            "Believes beautiful experiences are meant to be shared generously",
            "Depressed by penny-pinching austerity or aesthetic indifference",
        ],
        "dating_strengths": "Impeccable taste, generous hospitality, turns an ordinary evening into an event",
        "vulnerabilities": "Can be perceived as high-maintenance by minimalists",
        "synergistic_archetypes": ["high_velocity_strategist", "high_octane_catalyst", "visionary_builder"],
        "clashing_archetypes": ["intentional_minimalist"],
        "keywords": ["michelin", "fine dining", "wine", "aesthetic", "curated", "luxury", "design", "art", "architecture", "espresso", "opera", "cocktail"],
    },
    "holistic_seeker": {
        "id": "holistic_seeker",
        "name": "The Holistic Seeker",
        "tagline": "Mindfulness, nature-attuned living, somatic wellness, philosophical depth",
        "traits": [
            "Grounds life in breathwork, yoga, trail immersion, or meditation",
            "Prioritizes nervous-system regulation and authentic presence",
            "Seeks a partner with spiritual or somatic self-awareness",
            "Repelled by frantic hustle culture, cynical sarcasm, or superficial gossip",
        ],
        "dating_strengths": "Deep somatic calm, grounded nervous system, conscious presence",
        "vulnerabilities": "May struggle with partners who live purely in analytical or corporate head-space",
        "synergistic_archetypes": ["empathic_healer", "mindful_nomad", "contemplative_craftsman"],
        "clashing_archetypes": ["high_velocity_strategist", "high_octane_catalyst"],
        "keywords": ["yoga", "mindful", "meditation", "breathwork", "nature", "holistic", "wellness", "somatic", "hike", "presence", "zen", "trail"],
    },
    "playful_maverick": {
        "id": "playful_maverick",
        "name": "The Playful Maverick",
        "tagline": "Irreverent wit, playful banter, spontaneous adventure",
        "traits": [
            "Communicates through banter, humor, witty satire, and teasing",
            "Refuses to take life too seriously; defuses heavy moments with laughter",
            "Needs a partner with thick skin who can banter and roast back playfully",
            "Bored to tears by stiff, formal, or overly earnest conversations",
        ],
        "dating_strengths": "Instant laughter, magnetic lightness, dissolves awkwardness effortlessly",
        "vulnerabilities": "Can inadvertently sting sensitive partners; risks using humor as emotional armor",
        "synergistic_archetypes": ["high_octane_catalyst", "mindful_nomad", "visionary_builder"],
        "clashing_archetypes": ["empathic_healer", "contemplative_craftsman"],
        "keywords": ["comedy", "banter", "witty", "roast", "sarcasm", "playful", "improv", "teasing", "maverick", "irreverent", "humor", "joke"],
    },
}

# =====================================================================
# 2. Attachment Styles & Conflict Dynamics
# =====================================================================

ATTACHMENT_STYLES: dict[str, dict[str, str]] = {
    "secure": {
        "name": "Secure",
        "summary": "Comfortable with both emotional closeness and personal independence; communicates directly without fear of abandonment or engulfment.",
        "dating_behavior": "Transparent about feelings, respects boundaries, neither chases nor stonewalls.",
    },
    "anxious": {
        "name": "Anxious-Preoccupied",
        "summary": "Deeply expressive and warm, but sensitive to subtle shifts in emotional availability; craves reassurance and consistent presence.",
        "dating_behavior": "Highly attentive and responsive; needs clarity on where things stand to prevent overthinking.",
    },
    "avoidant": {
        "name": "Dismissive-Avoidant",
        "summary": "Fiercely self-reliant; uses independence or intellectual focus as emotional armor; recoils from premature emotional demands.",
        "dating_behavior": "Warm on light/intellectual topics, but takes time to open emotionally; requires respectful pace.",
    },
    "fearful": {
        "name": "Fearful-Avoidant (Disorganized)",
        "summary": "Desires deep vulnerability but fears getting hurt; vacillates between profound closeness and protective withdrawal.",
        "dating_behavior": "Deeply soulful when safe, but vigilant for red flags; appreciates patience and calm consistency.",
    },
}

CONFLICT_STYLES: dict[str, dict[str, str]] = {
    "collaborative": {
        "name": "Collaborative & Validating",
        "summary": "Validates partner's perspective first, separates ego from issue, and seeks win-win resolution.",
    },
    "processing_space": {
        "name": "Regulated Processing (Space First)",
        "summary": "Needs 30-60 minutes of quiet space to de-escalate physiological flooding before calm dialogue.",
    },
    "high_candor": {
        "name": "High-Candor Directness",
        "summary": "Prefers raw, immediate transparency over polite ambiguity; wants issues named right away.",
    },
    "gentle_deescalation": {
        "name": "Gentle De-escalation",
        "summary": "Uses warmth, soothing tone, and physical groundedness to de-escalate emotional tension.",
    },
}

# =====================================================================
# 3. Assessment Questions (Life, Work, Future, & Psychological Behavior)
# =====================================================================

PSYCHOLOGICAL_ASSESSMENT_SECTIONS = [
    {
        "id": "section_archetype",
        "title": "1. Psychological Archetype & Identity",
        "description": "Select or let AMORA infer your core relational archetype and emotional operating system.",
    },
    {
        "id": "section_life",
        "title": "2. Life Architecture & Relational Pacing",
        "description": "How you structure your days, recharge your battery, and your geographic roots.",
    },
    {
        "id": "section_work",
        "title": "3. Work Ethos & Ambition Horizons",
        "description": "How career ambition balances against evening boundaries and your financial philosophy.",
    },
    {
        "id": "section_future",
        "title": "4. Future Visions & Secret Dreams",
        "description": "Your 5-year horizon, secret passions, and what a transformative partnership unlocks.",
    },
    {
        "id": "section_psychology",
        "title": "5. Psychological Dynamics & Non-Negotiables",
        "description": "Attachment style, conflict response under stress, and hard dealbreakers.",
    },
]


# =====================================================================
# 4. Archetype & Behavioral Classifier
# =====================================================================

def classify_archetype(
    text_corpus: str,
    explicit_selection: Optional[str] = None,
) -> tuple[str, list[str]]:
    """Determine primary archetype and traits from response text or explicit selection."""
    if explicit_selection and explicit_selection in ARCHETYPES:
        arch = ARCHETYPES[explicit_selection]
        return arch["name"], arch["traits"]

    lower = text_corpus.lower()
    scores: dict[str, int] = {}
    for aid, arch in ARCHETYPES.items():
        score = sum(1 for kw in arch["keywords"] if kw in lower)
        scores[aid] = score

    best_aid = max(scores, key=lambda k: scores[k])
    # Fallback to Contemplative Craftsman if no keywords matched
    if scores[best_aid] == 0:
        best_aid = "contemplative_craftsman"

    arch = ARCHETYPES[best_aid]
    return arch["name"], arch["traits"]


def infer_attachment_style(text: str, explicit_choice: Optional[str] = None) -> str:
    """Infer attachment style from response text or explicit user choice."""
    if explicit_choice and explicit_choice in ATTACHMENT_STYLES:
        return ATTACHMENT_STYLES[explicit_choice]["name"]
    lower = text.lower()
    if any(k in lower for k in ["space", "independent", "overwhelm", "recoil", "self-reliant", "armor"]):
        return "Dismissive-Avoidant"
    if any(k in lower for k in ["reassur", "anxious", "clarity", "overthink", "text back", "abandon"]):
        return "Anxious-Preoccupied"
    if any(k in lower for k in ["guarded", "trust", "vigilant", "withdrawn", "push pull"]):
        return "Fearful-Avoidant"
    return "Secure"


def infer_conflict_style(text: str, explicit_choice: Optional[str] = None) -> str:
    """Infer conflict resolution style from response text or choice."""
    if explicit_choice and explicit_choice in CONFLICT_STYLES:
        return CONFLICT_STYLES[explicit_choice]["name"]
    lower = text.lower()
    if any(k in lower for k in ["30 min", "space", "time to process", "cool down", "walk away", "solitude"]):
        return "Regulated Processing (Space First)"
    if any(k in lower for k in ["direct", "candor", "blunt", "immediate", "straight away", "no filter"]):
        return "High-Candor Directness"
    if any(k in lower for k in ["humor", "laugh", "hug", "calm down", "gentle"]):
        return "Gentle De-escalation"
    return "Collaborative & Validating"


def extract_key_phrases(text: str, default: list[str]) -> list[str]:
    """Clean chunks into high-signal key phrases."""
    if not text:
        return default
    chunks = re.split(r"[,;\n]+", text)
    cleaned = [c.strip(" -•*") for c in chunks if len(c.strip(" -•*")) > 2]
    return cleaned[:6] if cleaned else default


# =====================================================================
# 5. Full Psychological Persona Synthesis (Zero-Scraping Onboarding)
# =====================================================================

def synthesize_psychological_persona(
    display_name: str,
    one_liner: str,
    answers: dict[str, str],
    pid: Optional[str] = None,
) -> Person:
    """Synthesize complete, compliant Person model grounded in psychological assessment.
    
    Zero scraping required. All claims are cited directly from the participant's authentic responses.
    """
    person_id = pid or f"user-{secrets.token_hex(4)}"
    clean_name = display_name.strip() or "Anonymous Dater"
    clean_headline = one_liner.strip() or "Autonomous AMORA Member"

    # Extract Life answers
    sunday = answers.get("sunday_rhythm", "").strip()
    geo_anchor = answers.get("geo_anchor", "").strip() or "Rooted in current city"
    family_vision = answers.get("family_vision", "").strip() or "Open to children in the right partnership"
    social_battery = answers.get("social_battery", "").strip() or "Balanced social battery; needs quiet recharge days"

    # Extract Work answers
    work_ambition = answers.get("work_ambition", "").strip() or "Balanced professional dedication with healthy evening boundaries"
    financial_philosophy = answers.get("financial_philosophy", "").strip() or "Intentional spending on experiences and stability"

    # Extract Future answers
    future_vision = answers.get("future_vision", "").strip() or "Building a peaceful, creative life and meaningful partnership"

    # Extract Psychological & Conflict answers
    conflict_raw = answers.get("conflict_style", "").strip()
    attachment_raw = answers.get("attachment_style", "").strip()
    dealbreakers_raw = answers.get("dealbreakers", "").strip()
    ideal_date = answers.get("ideal_date", "").strip() or "A cozy, quiet venue with authentic conversation and great atmosphere"
    archetype_pref = answers.get("archetype_preference", "").strip()

    # Combine corpus for behavioral inference
    corpus = f"{clean_headline} {sunday} {geo_anchor} {family_vision} {work_ambition} {financial_philosophy} {future_vision} {conflict_raw} {attachment_raw} {dealbreakers_raw}"
    
    archetype_name, archetype_traits = classify_archetype(corpus, explicit_selection=archetype_pref)
    attachment = infer_attachment_style(attachment_raw, explicit_choice=answers.get("attachment_choice"))
    conflict = infer_conflict_style(conflict_raw, explicit_choice=answers.get("conflict_choice"))

    dealbreakers = extract_key_phrases(dealbreakers_raw, default=["Disrespect for personal boundaries", "Emotional stonewalling"])
    hobbies = extract_key_phrases(sunday, default=["Reading", "Pour-over coffee", "Trail walks"])
    if future_vision:
        hobbies.extend(extract_key_phrases(future_vision, default=[])[:2])

    # Distinct values inferred from life & work responses
    values = ["Emotional Honesty", "Mutual Respect", "Intentional Living"]
    if any(k in corpus.lower() for k in ["family", "kids", "children", "roots"]):
        values.append("Family & Rooted Warmth")
    if any(k in corpus.lower() for k in ["startup", "build", "scale", "ambition", "growth"]):
        values.append("Ambition & Growth")
    if any(k in corpus.lower() for k in ["nature", "hike", "trail", "eco", "mountain"]):
        values.append("Nature & Wilderness")
    if any(k in corpus.lower() for k in ["art", "music", "design", "craft", "pottery"]):
        values.append("Creative Expression")
    if any(k in corpus.lower() for k in ["frugal", "fire", "minimalism", "save"]):
        values.append("Financial Freedom")

    # Inferred behavioral patterns
    patterns = [
        f"Archetype: {archetype_name}",
        f"Attachment dynamic: {attachment} pattern",
        f"Conflict handling: {conflict}",
        f"Social battery: {social_battery[:60]}",
    ]
    if "quiet" in sunday.lower() or "silence" in sunday.lower():
        patterns.append("Thrives in comfortable silence & parallel creative focus")
    if "startup" in work_ambition.lower() or "80" in work_ambition.lower():
        patterns.append("High-velocity founder work drive requiring clear boundary negotiation")

    # Grounded evidence items citing user's exact input (Zero Web Scraping)
    evidence_items = [
        Evidence(
            claim=f"Psychological Archetype: {archetype_name}",
            source="psychological_intake",
            snippet=f"Assessment response: '{clean_headline[:100]}'",
        ),
        Evidence(
            claim=f"Attachment Dynamic: {attachment}",
            source="psychological_intake",
            snippet=f"Psychological profile: '{attachment_raw[:100] if attachment_raw else attachment}'",
        ),
        Evidence(
            claim=f"Conflict Style: {conflict}",
            source="psychological_intake",
            snippet=f"Conflict response: '{conflict_raw[:100] if conflict_raw else conflict}'",
        ),
        Evidence(
            claim=f"Sunday Pace: {sunday[:40]}",
            source="psychological_intake",
            snippet=f"Life architecture: '{sunday[:120]}'",
        ),
    ]
    if dealbreakers:
        evidence_items.append(
            Evidence(
                claim=f"Non-Negotiable Boundary: {dealbreakers[0]}",
                source="psychological_intake",
                snippet=f"Boundary disclosure: '{dealbreakers_raw[:120]}'",
            )
        )
    if future_vision:
        evidence_items.append(
            Evidence(
                claim="5-Year Horizon & Secret Dream",
                source="psychological_intake",
                snippet=f"Future vision: '{future_vision[:120]}'",
            )
        )

    # Core relationship needs based on archetype + life architecture
    needs = [
        f"A partner whose pacing aligns with {archetype_name}",
        f"Emotional safety matching a {attachment.lower()} attachment style",
        f"Conflict resolution honoring {conflict.lower()}",
    ]
    if "root" in geo_anchor.lower() or "stay" in geo_anchor.lower():
        needs.append("A partner committed to local stability (no sudden international relocation)")
    elif "nomad" in geo_anchor.lower() or "travel" in geo_anchor.lower():
        needs.append("A fellow traveler open to geographic mobility and exploration")

    life_dict = {
        "pace": sunday[:50] or "Balanced living",
        "social_energy": social_battery[:50] or "Balanced",
        "mobility": geo_anchor[:50],
        "family_vision": family_vision[:50],
    }

    work_dict = {
        "ambition_pace": work_ambition[:50],
        "financial_philosophy": financial_philosophy[:50],
    }

    summary = (
        f"{clean_name} embodies {archetype_name} with a {attachment.lower()} attachment dynamic. "
        f"In life: {life_dict['pace'].lower()}; geographic anchor: {geo_anchor.lower()}. "
        f"In work: {work_ambition.lower()}. Secret 5-year vision: {future_vision.lower()}."
    )

    analysis = Analysis(
        display_name=clean_name,
        one_liner=f"{clean_headline} · {archetype_name}",
        summary=summary,
        needs=needs[:4],
        hobbies=hobbies[:6],
        interests=[hobbies[0] if hobbies else "Meaningful conversations", "Depth of character", "Personal evolution"],
        values=values[:5],
        personality=[archetype_traits[0], archetype_traits[1] if len(archetype_traits) > 1 else "Authentic", "Self-aware"],
        lifestyle=life_dict,
        communication_style=f"{conflict}; {attachment.lower()} intimacy comfort",
        green_flags=[
            "High psychological self-awareness",
            "Clear relational boundaries",
            "Aligned life & work pacing",
        ],
        dealbreakers=dealbreakers,
        ideal_date=ideal_date,
        conversation_starters=[
            f"What does an ideal Sunday look like when no one expects anything from you?",
            f"If you could build one secret project over the next 5 years, what would it be?",
            f"How do you prefer to navigate moments when things feel tense or misunderstood?",
        ],
        evidence=evidence_items,
        confidence=0.98,
        engine_used="psychological_archetype_profiler",
        archetype=archetype_name,
        archetype_traits=archetype_traits,
        attachment_style=attachment,
        conflict_style=conflict,
        life_architecture=life_dict,
        work_ethos=work_dict,
        future_horizon=future_vision,
        psychological_patterns=patterns,
    )

    # In compliance-first model, mock internal URLs for source bundle compatibility
    li_url = f"https://amora.app/profile/{person_id}"
    ig_url = f"https://amora.app/psych/{person_id}"

    sources = SourceBundle(
        linkedin=LinkedInData(
            url=li_url,
            full_name=clean_name,
            headline=f"{clean_headline} · {archetype_name}",
            about=f"Work Ethos: {work_ambition}\nFuture Horizon: {future_vision}",
        ),
        instagram=InstagramData(
            url=ig_url,
            username=clean_name.lower().replace(" ", "_"),
            full_name=clean_name,
            bio=f"Archetype: {archetype_name}. Sunday rhythm: {sunday}. Boundary: {dealbreakers[0] if dealbreakers else 'Respect'}",
        ),
    )

    # Coaching directives instructing the autonomous dating agent
    coaching = [
        f"Embody your human's psychological archetype: {archetype_name}.",
        f"Respect their attachment style ({attachment}): probe for emotional safety without being performative.",
        f"When conflict or differing opinions arise, embody their conflict style: {conflict}.",
        f"Probe gently on core boundaries: {dealbreakers[0]}." if dealbreakers else "Probe life pacing and future alignment.",
        f"Share their secret future vision when authentic: {future_vision[:80]}." if future_vision else "Look for genuine shared curiosity.",
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
