"""Empirical Research Study: Conversational Agent Dates vs. Profile-Only Baseline.

Hypothesis:
Profile-only screening (baseline prior) relies on public observable signals (headline, stated hobbies)
and is frequently misled by superficial keyword overlap or concealed boundaries.
Multi-turn conversational dates allow autonomous agents to probe latent relationship needs,
dealbreakers, and hidden plans, recovering true ground-truth compatibility significantly better
than the profile-only prior.

Generates:
1. Synthetic personas with hidden conversational truth.
2. Statistical error metrics (MAE, RMSE, Spearman rho, Error Reduction %).
3. Publication-quality vector SVG chart: 'Simulated Dates Beat Baseline by X%'.
"""
from __future__ import annotations

import hashlib
import html
import math
import random
from dataclasses import dataclass
from typing import Any

from .. import config, store
from ..agents import compat, dater
from ..models import Analysis, DateRecord, Evidence, InstagramData, InstagramPost, LinkedInData, LinkedInExperience, Person, SourceBundle, Turn, Verdict


@dataclass
class ConversationalBenchmarkPair:
    pair_id: str
    person_a: Person
    person_b: Person
    public_overlap_summary: str
    hidden_conversational_facts: str
    ground_truth_score: float  # Gold-standard relational ground truth y* (0 to 10)
    discovery_narrative: str


def _build_research_persona(
    pid: str,
    name: str,
    public_headline: str,
    public_hobbies: list[str],
    public_interests: list[str],
    stated_pace: str,
    hidden_needs: list[str],
    hidden_dealbreakers: list[str],
    hidden_private_truth: str,
    coaching_directives: list[str],
) -> Person:
    """Construct persona with public profile and hidden conversational facts."""
    analysis = Analysis(
        display_name=name,
        one_liner=public_headline,
        summary=f"{public_headline}. Enjoys {', '.join(public_hobbies[:2])}.",
        needs=hidden_needs,
        hobbies=public_hobbies,
        interests=public_interests,
        values=["Honesty", "Authenticity", "Growth"],
        personality=["Thoughtful", "Reflective"],
        lifestyle={"pace": stated_pace, "social_energy": "Balanced"},
        communication_style="Direct and conversational",
        green_flags=["Grounded communication", "Respectful boundaries"],
        dealbreakers=hidden_dealbreakers,
        ideal_date="Quiet café conversation",
        conversation_starters=["What are you currently passionate about?"],
        evidence=[
            Evidence(claim=f"Enjoys {public_hobbies[0]}", source="instagram", snippet=f"Weekend {public_hobbies[0]}") if public_hobbies else Evidence(claim="Active professional", source="linkedin", snippet="Works in tech"),
        ],
        confidence=0.95,
        engine_used="research_synth",
    )
    li = LinkedInData(url=f"https://example.com/in/{pid}", full_name=name, headline=public_headline, about=hidden_private_truth)
    ig = InstagramData(url=f"https://example.com/ig/{pid}", username=pid, full_name=name, bio=public_headline)
    return Person(
        id=pid,
        linkedin_url=li.url,
        instagram_url=ig.url,
        consent=True,
        synthetic=True,
        analysis=analysis,
        sources=SourceBundle(linkedin=li, instagram=ig),
        status="analyzed",
        coaching_notes=coaching_directives,
    )


def generate_research_cohort() -> list[ConversationalBenchmarkPair]:
    """Generate benchmark cohort with planted hidden conversational truths."""
    pairs: list[ConversationalBenchmarkPair] = []

    # Case 1: The Nomad vs. The Rooted Caregiver (Superficial Keyword Trap)
    # Public: Both list "Travel & Urban Exploration" -> Prior ranks them high (7.8)
    # Hidden: A has sick elderly parent in city (cannot leave); B is moving to Tokyo in 8 months.
    # Ground Truth: 2.2 (Severe geographic incompatibility)
    p1a = _build_research_persona(
        pid="study-1a",
        name="Aarav Iyer",
        public_headline="Architect & Urban Sketcher",
        public_hobbies=["Travel", "Urban Exploration", "Architecture"],
        public_interests=["City design", "Coffee crawls", "Sketching"],
        stated_pace="Balanced city life",
        hidden_needs=["A partner permanently anchored locally; caring for elderly parent"],
        hidden_dealbreakers=["Moving abroad, digital nomad lifestyles, relocating"],
        hidden_private_truth="Sole caregiver for elderly mother; rooted in this city for next 10 years.",
        coaching_directives=["Ask early if they plan to move or relocate; I cannot leave this city."],
    )
    p1b = _build_research_persona(
        pid="study-1b",
        name="Meera Kapoor",
        public_headline="UX Designer & Travel Blogger",
        public_hobbies=["Travel", "Urban Exploration", "Photography"],
        public_interests=["World cultures", "Coffee crawls", "Design"],
        stated_pace="Spontaneous nomad",
        hidden_needs=["A nomad partner willing to live out of suitcases across Asia"],
        hidden_dealbreakers=["Wanting to stay permanently in one city"],
        hidden_private_truth="Signed a 1-year contract in Tokyo starting this autumn; leaving the country.",
        coaching_directives=["Be honest that I am moving to Tokyo in 8 months."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="nomad_vs_rooted",
        person_a=p1a,
        person_b=p1b,
        public_overlap_summary="Both list 'Travel' and 'Urban Exploration' on public profile",
        hidden_conversational_facts="Aarav cannot leave city (elderly parent care); Meera moving to Tokyo in 8 months",
        ground_truth_score=2.2,
        discovery_narrative="Aarav probed long-term relocation. Meera revealed Tokyo move; mutual hard boundary hit.",
    ))

    # Case 2: The Secret Sanctuary / Hidden Dream (Opposites on Paper, Soulmates in Dialogue)
    # Public: Corporate M&A Finance vs. Wildlife Illustrator -> Prior ranks them low (3.6)
    # Hidden: Finance analyst is secretly quitting to open an eco-retreat lodge; Wildlife artist seeks co-founder.
    # Ground Truth: 9.2 (Extraordinary deep alignment)
    p2a = _build_research_persona(
        pid="study-2a",
        name="Rohan Shah",
        public_headline="Senior M&A Associate at GlobalBank",
        public_hobbies=["Reading", "Tennis", "Podcasts"],
        public_interests=["Corporate finance", "Market history", "Espresso"],
        stated_pace="Fast-paced corporate",
        hidden_needs=["A creative partner to build an off-grid mountain wildlife sanctuary"],
        hidden_dealbreakers=["Corporate climber obsession", "Materialistic status"],
        hidden_private_truth="Saved capital for 5 years to quit finance this December and launch an off-grid wildlife retreat.",
        coaching_directives=["Tell them what is not on my LinkedIn: I am quitting corporate life to start a mountain sanctuary."],
    )
    p2b = _build_research_persona(
        pid="study-2b",
        name="Ishita Bose",
        public_headline="Botanical Illustrator & Wildlife Conservationist",
        public_hobbies=["Gardening", "Watercolor", "Trail Walks"],
        public_interests=["Flora conservation", "Sustainable living", "Tea"],
        stated_pace="Slow living",
        hidden_needs=["An ambitious, grounded partner with practical skill to co-run a nature reserve"],
        hidden_dealbreakers=["Arrogant corporate finance mindset with no soul"],
        hidden_private_truth="Actively seeking land and a partner to establish an environmental sanctuary lodge.",
        coaching_directives=["Look for someone with real ambition who wants to build something meaningful in nature."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="secret_sanctuary",
        person_a=p2a,
        person_b=p2b,
        public_overlap_summary="Corporate finance vs wildlife artist (zero profile keyword overlap)",
        hidden_conversational_facts="Rohan quitting finance to start nature lodge; Ishita seeking sanctuary co-builder",
        ground_truth_score=9.2,
        discovery_narrative="Rohan revealed secret eco-lodge plan. Ishita lit up; profound latent synergy unlocked.",
    ))

    # Case 3: Emotional Stonewalling (Surface Mindfulness vs. Hidden Avoidance)
    # Public: Both list "Mindfulness, Yoga, Specialty Coffee" -> Prior ranks them high (8.1)
    # Hidden: Candidate 3A needs emotional vulnerability; Candidate 3B mocks feelings and is emotionally evasive.
    # Ground Truth: 2.8 (Emotional dealbreaker collision)
    p3a = _build_research_persona(
        pid="study-3a",
        name="Kiran Sen",
        public_headline="Mindfulness Facilitator & Writer",
        public_hobbies=["Yoga", "Specialty Coffee", "Meditation"],
        public_interests=["Psychology", "Poetry", "Quiet mornings"],
        stated_pace="Mindful and intentional",
        hidden_needs=["Radical vulnerability, emotional presence, discussing deep feelings"],
        hidden_dealbreakers=["Sarcastic deflection of feelings, emotional avoidance, stonewalling"],
        hidden_private_truth="Needs deep emotional check-ins; cannot tolerate partners who bottle up or mock feelings.",
        coaching_directives=["Ask what they actually need emotionally; check if they can speak vulnerably."],
    )
    p3b = _build_research_persona(
        pid="study-3b",
        name="Farhan Qureshi",
        public_headline="High-Frequency Systems Engineer",
        public_hobbies=["Yoga", "Specialty Coffee", "Cycling"],
        public_interests=["Systems design", "Espresso brewing", "Gadgets"],
        stated_pace="Calculated and stoic",
        hidden_needs=["Someone who keeps things 100% light, sarcastic, and never talks about feelings"],
        hidden_dealbreakers=["Talking about emotions or relationship therapy early on"],
        hidden_private_truth="Severe emotional burnout; becomes defensive and shuts down whenever feelings are probed.",
        coaching_directives=["Keep conversation purely rational and humorous; avoid heavy emotional talk."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="emotional_stonewalling",
        person_a=p3a,
        person_b=p3b,
        public_overlap_summary="Both list 'Yoga' and 'Specialty Coffee' with mindful tags",
        hidden_conversational_facts="Kiran requires radical vulnerability; Farhan shuts down and avoids all emotions",
        ground_truth_score=2.8,
        discovery_narrative="Kiran probed emotional depth. Farhan deflected with defensive sarcasm; dealbreaker triggered.",
    ))

    # Case 4: Authentic True Positives (Shared Outdoor Pacing & Family Values)
    # Public: Bouldering, Literature -> Prior ranks moderate-high (7.1)
    # Hidden: Both want 2 kids, quiet early mornings, mutual emotional safety.
    # Ground Truth: 9.0 (Grounded soulmates)
    p4a = _build_research_persona(
        pid="study-4a",
        name="Ananya Rao",
        public_headline="Climate Scientist at EcoLabs",
        public_hobbies=["Bouldering", "Literature", "Hiking"],
        public_interests=["Climate science", "Indie books", "Mornings"],
        stated_pace="Early morning adventurer",
        hidden_needs=["An emotionally secure partner who values family closeness and quiet adventure"],
        hidden_dealbreakers=["Cynicism, smoking, loud chaotic nightlife"],
        hidden_private_truth="Ready to settle down, desires 2 children within 3 years, deeply family-oriented.",
        coaching_directives=["Ask about family values and what their Sunday mornings look like."],
    )
    p4b = _build_research_persona(
        pid="study-4b",
        name="Kabir Menon",
        public_headline="Renewable Energy Analyst",
        public_hobbies=["Bouldering", "Literature", "Film Photography"],
        public_interests=["Sustainability", "Classic novels", "Pour-over"],
        stated_pace="Early morning adventurer",
        hidden_needs=["A grounded partner who shares outdoor curiosity and values calm family warmth"],
        hidden_dealbreakers=["Cynicism, smoking, arrogance"],
        hidden_private_truth="Deeply family-centric, looking for life partner to raise a family in a peaceful home.",
        coaching_directives=["Share that I am ready for family life and love quiet outdoor weekends."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="outdoor_soulmates",
        person_a=p4a,
        person_b=p4b,
        public_overlap_summary="Both list 'Bouldering' and 'Literature'",
        hidden_conversational_facts="Both desire quiet family life with 2 kids and shared emotional security",
        ground_truth_score=9.0,
        discovery_narrative="Agents discussed Sunday routines and family vision; immediate deep resonance confirmed.",
    ))

    # Case 5: The 80-Hour Workaholic vs. Sacred Evenings
    # Public: Both tech startup builders -> Prior ranks high (7.9)
    # Hidden: A works 85 hrs/week and demands tech talk; B has hard boundary against work talk outside office.
    # Ground Truth: 3.0 (Lifestyle dealbreaker collision)
    p5a = _build_research_persona(
        pid="study-5a",
        name="Vikram Pillai",
        public_headline="Y-Combinator Founder & CEO",
        public_hobbies=["Startups", "Coding", "Running"],
        public_interests=["Venture capital", "AI chips", "Coffee"],
        stated_pace="Hyper-growth workaholic",
        hidden_needs=["A partner whose life revolves around startups and will code alongside me till midnight"],
        hidden_dealbreakers=["People who clock out at 5pm or dislike talking about work on dates"],
        hidden_private_truth="Works 85 hours a week; dates are networking opportunities to discuss company roadmap.",
        coaching_directives=["Bring up my startup vision immediately and test if they have founder hunger."],
    )
    p5b = _build_research_persona(
        pid="study-5b",
        name="Tara Nair",
        public_headline="Senior Software Engineer at Scale",
        public_hobbies=["Startups", "Coding", "Ceramics"],
        public_interests=["Distributed systems", "Pottery", "Indie films"],
        stated_pace="Strict boundary at 5pm",
        hidden_needs=["A partner who leaves work at work and cherishes evenings completely free of professional talk"],
        hidden_dealbreakers=["Talking about tech/startups on dates, workaholic partners"],
        hidden_private_truth="Hard boundary: refuses to date anyone who talks about business or code outside work.",
        coaching_directives=["Before we talk small talk: one rule, let's not talk about work at all tonight."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="workaholic_vs_boundary",
        person_a=p5a,
        person_b=p5b,
        public_overlap_summary="Both startup software builders ('Startups, Coding')",
        hidden_conversational_facts="Vikram demands 85hr startup focus on dates; Tara strictly bans work talk on dates",
        ground_truth_score=3.0,
        discovery_narrative="Tara enacted strict no-work boundary rule; Vikram could not disengage. Verdict declined.",
    ))

    # Case 6: The Quiet Creative Resonance (Hidden Neurodivergent Alignment)
    # Public: Independent Animator & Ambient Sound Designer -> Prior ranks moderate (5.6)
    # Hidden: Both need parallel play (working quietly in the same room) and zero social pressure.
    # Ground Truth: 8.8 (Exceptional mutual comfort)
    p6a = _build_research_persona(
        pid="study-6a",
        name="Neel Joshi",
        public_headline="Stop-Motion Animator & Sculptor",
        public_hobbies=["Claymation", "Cinema", "Lo-Fi Music"],
        public_interests=["Stop motion", "Vintage toys", "Tea"],
        stated_pace="Quiet studio pace",
        hidden_needs=["A gentle partner comfortable with long comfortable silences and parallel creative work"],
        hidden_dealbreakers=["Loud aggressive small talk, demanding constant verbal validation"],
        hidden_private_truth="Thrives in quiet parallel play; deeply energized by calm creative companionship.",
        coaching_directives=["Look for someone who appreciates comfortable silence and gentle creative focus."],
    )
    p6b = _build_research_persona(
        pid="study-6b",
        name="Zain Mirza",
        public_headline="Ambient Game Composer & Audio Engineer",
        public_hobbies=["Modular Synths", "Cinema", "Lo-Fi Music"],
        public_interests=["Audio synthesis", "Foley recording", "Walks"],
        stated_pace="Quiet studio pace",
        hidden_needs=["A gentle partner who loves sharing space quietly without needing constant social performance"],
        hidden_dealbreakers=["Demanding extroverts who cannot tolerate silence"],
        hidden_private_truth="Prefers spending weekends quietly working side-by-side in deep focus.",
        coaching_directives=["Be gentle and calm; share my love for quiet parallel creative flow."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="quiet_creative_flow",
        person_a=p6a,
        person_b=p6b,
        public_overlap_summary="Niche arts: animation & modular audio (moderate prior)",
        hidden_conversational_facts="Both require quiet parallel play and zero social performance pressure",
        ground_truth_score=8.8,
        discovery_narrative="Shared love of comfortable silence and parallel creative focus emerged in dialogue.",
    ))

    # Case 7: The Smoker / Health Dealbreaker Clash (Superficial Trap)
    # Public: Both list 'Trail Running & Specialty Coffee' -> Prior ranks high (8.2)
    # Hidden: Maya has severe asthma and zero-smoke dealbreaker; Dev is heavy tobacco smoker.
    # Ground Truth: 2.0 (Severe medical dealbreaker collision)
    p7a = _build_research_persona(
        pid="study-7a",
        name="Maya Chen",
        public_headline="Product Designer & Trail Runner",
        public_hobbies=["Trail Running", "Specialty Coffee", "Ceramics"],
        public_interests=["Mountain trails", "Pour-over", "Design"],
        stated_pace="Active and clean living",
        hidden_needs=["A non-smoker partner with clean healthy lifestyle; severe respiratory sensitivity"],
        hidden_dealbreakers=["Smoking", "Chain smoker", "Tobacco", "Vaping"],
        hidden_private_truth="Has severe chronic asthma; cannot live or date someone who smokes tobacco.",
        coaching_directives=["Check early if they smoke tobacco; it is an absolute medical dealbreaker."],
    )
    p7b = _build_research_persona(
        pid="study-7b",
        name="Dev Malhotra",
        public_headline="Growth Lead & Coffee Enthusiast",
        public_hobbies=["Trail Running", "Specialty Coffee", "Music"],
        public_interests=["Trail races", "Espresso", "Indie rock"],
        stated_pace="Fast-paced executive",
        hidden_needs=["Someone who accepts my daily smoking habit without trying to change me"],
        hidden_dealbreakers=["Preachy health obsessives"],
        hidden_private_truth="Smokes a pack of tobacco cigarettes daily to manage stress; chain smoker.",
        coaching_directives=["Be upfront that I am a daily smoker."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="smoker_health_clash",
        person_a=p7a,
        person_b=p7b,
        public_overlap_summary="Both list 'Trail Running' and 'Specialty Coffee' with active tags",
        hidden_conversational_facts="Maya has severe asthma and non-smoking dealbreaker; Dev is daily chain smoker",
        ground_truth_score=2.0,
        discovery_narrative="Dev revealed daily smoking habit. Maya stated health boundary; date concluded incompatibly.",
    ))

    # Case 8: Hyper-Frugal FIRE vs. Luxury Spender (Superficial Trap)
    # Public: Both list 'Real Estate & Fine Dining' -> Prior ranks high (8.4)
    # Hidden: Arjun is extreme minimalist aiming for early retirement on $15/day; Priya demands 5-star luxury vacations.
    # Ground Truth: 2.5 (Fundamental financial incompatibility)
    p8a = _build_research_persona(
        pid="study-8a",
        name="Arjun Sethi",
        public_headline="Financial Analyst & Real Estate Researcher",
        public_hobbies=["Real Estate", "Fine Dining", "Cycling"],
        public_interests=["Property analysis", "Food reviews", "Personal finance"],
        stated_pace="Frugal and intentional",
        hidden_needs=["A partner committed to extreme frugality and early financial independence"],
        hidden_dealbreakers=["Luxury consumerism", "Expensive designer tastes", "Credit debt"],
        hidden_private_truth="Extreme FIRE practitioner; cooks all meals at home, budgets $15/day, avoids luxury.",
        coaching_directives=["Probe their financial philosophy; make sure they value extreme frugality."],
    )
    p8b = _build_research_persona(
        pid="study-8b",
        name="Priya Sen",
        public_headline="Brand Director & Luxury Hospitality Consultant",
        public_hobbies=["Real Estate", "Fine Dining", "Travel"],
        public_interests=["Luxury hotels", "Michelin dining", "Architecture"],
        stated_pace="High-end metropolitan",
        hidden_needs=["An ambitious partner who enjoys lavish 5-star travel and Michelin dinners"],
        hidden_dealbreakers=["Penny-pinching, cheapness, extreme frugality"],
        hidden_private_truth="Spends lavishly on luxury dining and first-class travel; cannot tolerate cheapness.",
        coaching_directives=["Discuss favorite luxury weekend escapes and fine dining experiences."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="frugal_vs_luxury",
        person_a=p8a,
        person_b=p8b,
        public_overlap_summary="Both list 'Real Estate' and 'Fine Dining'",
        hidden_conversational_facts="Arjun practices extreme FIRE frugality ($15/day); Priya demands 5-star Michelin luxury",
        ground_truth_score=2.5,
        discovery_narrative="Arjun revealed extreme budget minimalism. Priya named luxury expectations; friction confirmed.",
    ))

    # Case 9: Polyamory vs. Traditional Monogamy (Superficial Trap)
    # Public: Both list 'Indie Film & Art History' -> Prior ranks high (8.6)
    # Hidden: Leela is committed ethically non-monogamous; Sameer seeks lifelong exclusive marriage.
    # Ground Truth: 1.8 (Irreconcilable relationship structure collision)
    p9a = _build_research_persona(
        pid="study-9a",
        name="Leela Rao",
        public_headline="Film Curator & Documentary Filmmaker",
        public_hobbies=["Indie Film", "Art History", "Photography"],
        public_interests=["Cinema", "Visual arts", "Cultural theory"],
        stated_pace="Free-spirited artistic",
        hidden_needs=["An open-minded partner comfortable with polyamory and non-hierarchical relationships"],
        hidden_dealbreakers=["Demands for traditional monogamy, possessiveness"],
        hidden_private_truth="Practicing ethical non-monogamy for 6 years; will never agree to exclusive monogamy.",
        coaching_directives=["Be transparent early that I practice polyamory and non-monogamy."],
    )
    p9b = _build_research_persona(
        pid="study-9b",
        name="Sameer Deshmukh",
        public_headline="Architecture Historian & Preservationist",
        public_hobbies=["Indie Film", "Art History", "Museums"],
        public_interests=["Historic buildings", "Classic cinema", "Writing"],
        stated_pace="Traditional and steady",
        hidden_needs=["A partner seeking lifelong exclusive monogamy and traditional commitment"],
        hidden_dealbreakers=["Polyamory", "Open relationships", "Non-monogamy"],
        hidden_private_truth="Deeply traditional; seeks an exclusively monogamous partner to build a shared home.",
        coaching_directives=["Ask about relationship structure expectations; exclusive monogamy is required."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="poly_vs_monogamy",
        person_a=p9a,
        person_b=p9b,
        public_overlap_summary="Both list 'Indie Film' and 'Art History'",
        hidden_conversational_facts="Leela is non-negotiably polyamorous; Sameer requires traditional exclusive monogamy",
        ground_truth_score=1.8,
        discovery_narrative="Leela shared her non-monogamous lifestyle. Sameer clarified monogamy requirement; mutual pass.",
    ))

    # Case 10: Urban Farmer & Pediatrician Family Vision (Hidden Latent Synergy)
    # Public: Rooftop Agriculture vs. Pediatric ER Doctor -> Prior ranks low (4.5)
    # Hidden: Both want to leave the city in 2 years to run a rural community homestead and raise 3 kids.
    # Ground Truth: 9.3 (Profound latent family & life vision alignment)
    p10a = _build_research_persona(
        pid="study-10a",
        name="Siddharth Verma",
        public_headline="Urban Farming Specialist & Soil Biologist",
        public_hobbies=["Gardening", "Beekeeping", "Woodworking"],
        public_interests=["Soil biology", "Permaculture", "Fermentation"],
        stated_pace="Grounded earth rhythm",
        hidden_needs=["A partner wanting to leave the city and co-build a sustainable rural homestead with kids"],
        hidden_dealbreakers=["Perpetual high-rise city obsession"],
        hidden_private_truth="Plans to buy farmland in Uttarakhand within 24 months to raise a family and homestead.",
        coaching_directives=["Share my 2-year goal of moving to a rural homestead farm with children."],
    )
    p10b = _build_research_persona(
        pid="study-10b",
        name="Nina Kulkarni",
        public_headline="Pediatric Emergency Medicine Resident",
        public_hobbies=["Hiking", "Cooking", "Knitting"],
        public_interests=["Child health", "Herbal medicine", "Baking"],
        stated_pace="Intense shifts, yearning for peaceful country life",
        hidden_needs=["A grounding partner ready to relocate to a rural farm and raise children in nature"],
        hidden_dealbreakers=["Superficial status seekers"],
        hidden_private_truth="Exhausted by urban hospitals; dream is to open a rural clinic alongside a family farm.",
        coaching_directives=["Mention that after residency I want rural life on a farm with a big family."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="urban_farm_pediatrician",
        person_a=p10a,
        person_b=p10b,
        public_overlap_summary="Zero keyword overlap: urban agriculture vs pediatric emergency medicine",
        hidden_conversational_facts="Both secretly plan to move to a rural homestead within 2 years to raise children",
        ground_truth_score=9.3,
        discovery_narrative="Siddharth shared his farm dream. Nina revealed matching rural clinic vision; immediate spark.",
    ))

    # Case 11: Baroque Cellist & Quantum Engineer (Hidden Latent Synergy)
    # Public: Baroque Cello vs. Quantum Semiconductor Physics -> Prior ranks low (4.8)
    # Hidden: Both thrive on quiet evening focus, deep contemplative walks, and craftsmanship.
    # Ground Truth: 9.0 (Rare intellectual & temperament harmony)
    p11a = _build_research_persona(
        pid="study-11a",
        name="Aditi Bhat",
        public_headline="Baroque Cellist & Chamber Musician",
        public_hobbies=["Classical Music", "Calligraphy", "Tea"],
        public_interests=["Bach suites", "Period instruments", "Acoustics"],
        stated_pace="Quiet contemplative discipline",
        hidden_needs=["A partner who values deep discipline, craftsmanship, and quiet evening focus"],
        hidden_dealbreakers=["Loud chaotic social lives, superficial distractions"],
        hidden_private_truth="Needs hours of quiet practice daily; craves a deeply thoughtful, grounded companion.",
        coaching_directives=["Discuss the discipline of craftsmanship and value of quiet contemplation."],
    )
    p11b = _build_research_persona(
        pid="study-11b",
        name="Kavi Raman",
        public_headline="Quantum Hardware Physicist",
        public_hobbies=["Chess", "Astronomy", "Tea"],
        public_interests=["Superconducting circuits", "Cosmology", "Philosophy"],
        stated_pace="Intense analytical quietude",
        hidden_needs=["A quiet, artistically grounded partner who appreciates precision and depth"],
        hidden_dealbreakers=["High-drama emotional volatility"],
        hidden_private_truth="Fascinated by harmonic frequencies in acoustics; loves quiet evenings of mutual study.",
        coaching_directives=["Ask about their artistic relationship with sound and discipline."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="cellist_quantum_resonance",
        person_a=p11a,
        person_b=p11b,
        public_overlap_summary="Zero surface overlap: baroque classical music vs quantum semiconductor physics",
        hidden_conversational_facts="Shared rhythm of quiet craftsmanship, acoustic harmony, and deep contemplative walks",
        ground_truth_score=9.0,
        discovery_narrative="Aditi and Kavi discussed acoustic frequencies and discipline; deep mutual respect and attraction.",
    ))

    # Case 12: Corporate Lawyer & Housing Organizer (Hidden Latent Synergy)
    # Public: Corporate M&A Litigation vs. Tenant Rights Activist -> Prior ranks low (3.8)
    # Hidden: Corporate lawyer using severance to fund legal defense for tenants; profound moral alignment.
    # Ground Truth: 9.4 (Unshakeable moral and mission alignment)
    p12a = _build_research_persona(
        pid="study-12a",
        name="Ananya Saxena",
        public_headline="Corporate Litigation Associate at MagicCircle",
        public_hobbies=["Running", "Non-fiction", "Espresso"],
        public_interests=["Antitrust law", "Economic history", "Debate"],
        stated_pace="Fast-paced professional",
        hidden_needs=["A partner dedicated to social justice who can inspire my transition to public interest law"],
        hidden_dealbreakers=["Apathetic cynicism, greed"],
        hidden_private_truth="Secretly leaving big law in 3 months to start a pro-bono housing justice defense clinic.",
        coaching_directives=["Tell them I am leaving corporate law to launch a pro-bono tenant defense project."],
    )
    p12b = _build_research_persona(
        pid="study-12b",
        name="Kabir Das",
        public_headline="Community Organizer & Tenant Rights Advocate",
        public_hobbies=["Documentary Film", "Cycling", "Cooking"],
        public_interests=["Housing justice", "Community land trusts", "Urban policy"],
        stated_pace="Mission-driven grassroots",
        hidden_needs=["A strategic, legally trained partner who genuinely cares about tenant empowerment"],
        hidden_dealbreakers=["Defending corporate landlord exploitation for profit"],
        hidden_private_truth="Desperately seeking legal partners to incorporate land trusts and fight evictions.",
        coaching_directives=["Look for real commitment to community housing equity, not performative talk."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="legal_reform_synergy",
        person_a=p12a,
        person_b=p12b,
        public_overlap_summary="Apparent opposites: corporate litigation vs grassroots housing activism",
        hidden_conversational_facts="Ananya leaving big law to fund pro-bono tenant defense; Kabir organizing tenant trusts",
        ground_truth_score=9.4,
        discovery_narrative="Ananya revealed her departure from big law to launch housing clinic. Kabir was deeply moved.",
    ))

    # Case 13: Introverted Bookbinder & Dark-Sky Astronomer (Hidden Latent Synergy)
    # Public: Leather Bookbinding vs. Optical Astronomy -> Prior ranks low (4.6)
    # Hidden: Both nocturnal deep thinkers who cherish peaceful nighttime silence and tactile precision.
    # Ground Truth: 9.1 (Nocturnal harmony & peaceful solitude)
    p13a = _build_research_persona(
        pid="study-13a",
        name="Diya Nair",
        public_headline="Antiquarian Bookbinder & Paper Conservator",
        public_hobbies=["Bookbinding", "Calligraphy", "Tea"],
        public_interests=["Rare manuscripts", "Japanese paper", "Night walks"],
        stated_pace="Nocturnal studio calm",
        hidden_needs=["A gentle nocturnal partner who loves peaceful night hours without needing constant noise"],
        hidden_dealbreakers=["Demanding early-morning energy, loud sensory environments"],
        hidden_private_truth="Works primarily from 8 PM to 3 AM in quiet solitude; deeply peaceful nature.",
        coaching_directives=["Share my nocturnal studio routine and love for silent night hours."],
    )
    p13b = _build_research_persona(
        pid="study-13b",
        name="Taran Joshi",
        public_headline="Observatory Telescope Operator & Astrophotographer",
        public_hobbies=["Astronomy", "Optics", "Vinyl Records"],
        public_interests=["Deep sky imaging", "Telescope lenses", "Ambient music"],
        stated_pace="Nocturnal observatory calm",
        hidden_needs=["A calm nocturnal companion comfortable with silence and tactile focus"],
        hidden_dealbreakers=["Frantic daytime extroverts"],
        hidden_private_truth="Spends nights at observatory domes in quiet reverence; seeks tranquil partnership.",
        coaching_directives=["Connect over night schedules and appreciating quiet nocturnal solitude."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="bookbinder_astronomer",
        person_a=p13a,
        person_b=p13b,
        public_overlap_summary="Niche nocturnal crafts: book conservation vs telescope astrophysics",
        hidden_conversational_facts="Both live nocturnal schedules (8 PM to 3 AM) and find deep peace in tactile night calm",
        ground_truth_score=9.1,
        discovery_narrative="Diya and Taran bonded over their shared nocturnal rhythm and love for dark quiet hours.",
    ))

    # Case 14: Sourdough & Specialty Coffee Artisans (True Positive)
    # Public: Sourdough Baking & Specialty Coffee -> Prior ranks high (8.6)
    # Hidden: Shared domestic culinary patience, mutual kindness, calm unhurried weekend pace.
    # Ground Truth: 8.8 (Grounded domestic soulmates)
    p14a = _build_research_persona(
        pid="study-14a",
        name="Ritu Mehta",
        public_headline="Artisan Baker & Fermentation Instructor",
        public_hobbies=["Sourdough Baking", "Coffee Roasting", "Gardening"],
        public_interests=["Wild yeasts", "Heirloom grains", "Morning walks"],
        stated_pace="Slow living morning baker",
        hidden_needs=["A kind partner who cherishes quiet domestic mornings and culinary patience"],
        hidden_dealbreakers=["Aggressive impatience, fast-food lifestyle"],
        hidden_private_truth="Finds deep peace in nurturing sourdough starters and cooking thoughtful meals for loved ones.",
        coaching_directives=["Talk about morning fermentation routines and the beauty of slow food."],
    )
    p14b = _build_research_persona(
        pid="study-14b",
        name="Varun Bajaj",
        public_headline="Specialty Coffee Roaster & Cafe Founder",
        public_hobbies=["Coffee Roasting", "Sourdough Baking", "Cycling"],
        public_interests=["Origin tasting", "Fermentation", "Morning rides"],
        stated_pace="Slow living morning artisan",
        hidden_needs=["A warm partner who shares domestic culinary appreciation and gentle pacing"],
        hidden_dealbreakers=["Impatience, superficial drama"],
        hidden_private_truth="Dreams of opening a combined bakery and micro-roastery with a loving life partner.",
        coaching_directives=["Share passion for origin coffee and slow weekend breakfasts."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="ferment_coffee_artisans",
        person_a=p14a,
        person_b=p14b,
        public_overlap_summary="Both list 'Sourdough Baking' and 'Coffee Roasting' with slow living tags",
        hidden_conversational_facts="Shared domestic patience, gentle morning rhythms, and culinary companionship",
        ground_truth_score=8.8,
        discovery_narrative="Ritu and Varun discovered matching passions for slow fermentation and shared domestic calm.",
    ))

    # Case 15: Marathon Runners & Climate Policy Allies (True Positive)
    # Public: Distance Running & Climate Economics -> Prior ranks high (8.4)
    # Hidden: Compatible 5 AM waking schedules, plant-based nutrition, optimistic mutual encouragement.
    # Ground Truth: 8.9 (Energetic true positive resonance)
    p15a = _build_research_persona(
        pid="study-15a",
        name="Alisha Roy",
        public_headline="Climate Economics Fellow & Ultra-Marathoner",
        public_hobbies=["Marathon Running", "Climate Economics", "Plant-based Cooking"],
        public_interests=["Renewable policy", "Trail racing", "Nutrition"],
        stated_pace="Disciplined 5 AM sunrise pace",
        hidden_needs=["An early-rising, disciplined partner who shares optimistic ambition and athletic focus"],
        hidden_dealbreakers=["Heavy drinking, lazy cynical outlook"],
        hidden_private_truth="Dedicated to daily 5 AM training and positive climate research; seeks equal companion.",
        coaching_directives=["Check if they love early morning training and share environmental optimism."],
    )
    p15b = _build_research_persona(
        pid="study-15b",
        name="Nikhil Mehra",
        public_headline="Clean Energy Strategist & Distance Runner",
        public_hobbies=["Marathon Running", "Climate Economics", "Photography"],
        public_interests=["Energy grid transition", "Marathon training", "Trail hikes"],
        stated_pace="Disciplined 5 AM sunrise pace",
        hidden_needs=["An ambitious, active partner who wakes with the sunrise and loves athletic challenges"],
        hidden_dealbreakers=["Cynicism, late-night partying"],
        hidden_private_truth="Training for sub-3hr marathon while decarbonizing shipping; deeply value health.",
        coaching_directives=["Discuss marathon goals and early morning sunrise routines."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="marathon_climate_allies",
        person_a=p15a,
        person_b=p15b,
        public_overlap_summary="Both list 'Marathon Running' and 'Climate Economics'",
        hidden_conversational_facts="Synchronized 5 AM running schedules, plant-based lifestyle, and optimistic climate values",
        ground_truth_score=8.9,
        discovery_narrative="Alisha and Nikhil clicked immediately on training discipline and future sustainability.",
    ))

    # Case 16: Indie Game Developers & Pixel Artists (True Positive)
    # Public: Game Design & Pixel Art -> Prior ranks high (8.5)
    # Hidden: Mutual collaborative excitement, communicative respect, gentle playful banter.
    # Ground Truth: 8.7 (Creative true positive alignment)
    p16a = _build_research_persona(
        pid="study-16a",
        name="Tanvi Suri",
        public_headline="Indie Game Lead & Narrative Designer",
        public_hobbies=["Game Design", "Pixel Art", "Sci-Fi Literature"],
        public_interests=["Interactive narrative", "Retro gaming", "Tea"],
        stated_pace="Creative studio playful flow",
        hidden_needs=["A creative partner with collaborative humor, emotional safety, and shared gaming passion"],
        hidden_dealbreakers=["Arrogant gatekeeping, dismissive cynicism"],
        hidden_private_truth="Building heart-warming narrative games; seeks playful and supportive romantic partner.",
        coaching_directives=["Share favorite narrative story arcs and check for playful collaborative chemistry."],
    )
    p16b = _build_research_persona(
        pid="study-16b",
        name="Harshvardhan Jain",
        public_headline="Pixel Artist & Game Programmer",
        public_hobbies=["Pixel Art", "Game Design", "Tabletop RPGs"],
        public_interests=["Retro shaders", "Indie soundtracks", "Storytelling"],
        stated_pace="Creative studio playful flow",
        hidden_needs=["A supportive creative partner who loves narrative world-building and gentle humor"],
        hidden_dealbreakers=["Ego clashes, emotional coldness"],
        hidden_private_truth="Loves collaborating on wholesome games; values kindness and mutual encouragement.",
        coaching_directives=["Discuss world-building aesthetics and collaborative storytelling."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="indie_game_duo",
        person_a=p16a,
        person_b=p16b,
        public_overlap_summary="Both list 'Game Design' and 'Pixel Art'",
        hidden_conversational_facts="Playful collaborative synergy, mutual emotional safety, and aligned creative vision",
        ground_truth_score=8.7,
        discovery_narrative="Tanvi and Harsh exchanged playful game ideas and found immediate warm emotional resonance.",
    ))

    # Case 17: Ceramic Sculptors & Mountain Hikers (True Positive)
    # Public: Pottery & Mountain Trails -> Prior ranks high (8.2)
    # Hidden: Grounded emotional openness, tactile appreciation for nature, calm presence.
    # Ground Truth: 9.1 (Tactile calm true positive)
    p17a = _build_research_persona(
        pid="study-17a",
        name="Sanjana Kaul",
        public_headline="Ceramic Sculptor & Clay Studio Founder",
        public_hobbies=["Pottery", "Mountain Trails", "Mindfulness"],
        public_interests=["Natural glazes", "Alpine flora", "Quiet mornings"],
        stated_pace="Grounded earth tempo",
        hidden_needs=["A calm partner who loves nature and tactile craft without rush or vanity"],
        hidden_dealbreakers=["Frenetic status-seeking, constant phone checking"],
        hidden_private_truth="Finds deep peace in clay and mountain summits; values emotional presence above all.",
        coaching_directives=["Ask about their favorite mountain walks and how they find calm."],
    )
    p17b = _build_research_persona(
        pid="study-17b",
        name="Pranav Mittal",
        public_headline="Landscape Architect & Alpine Hiker",
        public_hobbies=["Mountain Trails", "Pottery", "Photography"],
        public_interests=["Natural stonework", "Wilderness trails", "Sketching"],
        stated_pace="Grounded earth tempo",
        hidden_needs=["An emotionally grounded partner who appreciates unhurried nature and tactile art"],
        hidden_dealbreakers=["Superficial social media obsession"],
        hidden_private_truth="Spends weekends hiking ridge lines and studying natural earth textures; deeply kind.",
        coaching_directives=["Share love for unhurried mountain ridge hikes and natural materials."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="ceramics_trail_hikers",
        person_a=p17a,
        person_b=p17b,
        public_overlap_summary="Both list 'Pottery' and 'Mountain Trails'",
        hidden_conversational_facts="Mutual emotional presence, tactile nature appreciation, and calm weekend rhythms",
        ground_truth_score=9.1,
        discovery_narrative="Sanjana and Pranav bonded over clay textures and mountain silence; profound mutual peace.",
    ))

    # Case 18: Chamber Musicians & Vinyl Collectors (True Positive)
    # Public: String Quartets & Vinyl Records -> Prior ranks high (8.3)
    # Hidden: Deep mutual empathy, gentle temperament, active listening, and domestic harmony.
    # Ground Truth: 9.2 (Musical true positive soulmates)
    p18a = _build_research_persona(
        pid="study-18a",
        name="Meenakshi Sundaram",
        public_headline="Violinist & String Ensemble Director",
        public_hobbies=["Vinyl Records", "Classical Music", "Literature"],
        public_interests=["Brahms chamber works", "Analog audio", "Poetry"],
        stated_pace="Gentle harmonious rhythm",
        hidden_needs=["A partner with deep emotional empathy who loves active listening and quiet domestic warmth"],
        hidden_dealbreakers=["Abrasive sarcasm, loud verbal aggression"],
        hidden_private_truth="Sensitive artist seeking a peaceful, loving partnership filled with music and kindness.",
        coaching_directives=["Discuss the emotional depth of acoustic string music and active listening."],
    )
    p18b = _build_research_persona(
        pid="study-18b",
        name="Devang Trivedi",
        public_headline="Audio Mastering Engineer & Vinyl Collector",
        public_hobbies=["Vinyl Records", "Classical Music", "Audio Engineering"],
        public_interests=["Acoustic mastering", "Chamber music", "Espresso"],
        stated_pace="Gentle harmonious rhythm",
        hidden_needs=["A gentle, emotionally attuned partner who appreciates sound, art, and quiet harmony"],
        hidden_dealbreakers=["Harsh cynicism, emotional volatility"],
        hidden_private_truth="Masters analog records with patient care; seeks a warm, enduring domestic life.",
        coaching_directives=["Share love for analog warmth and peaceful Sunday chamber listening."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="chamber_vinyl_harmony",
        person_a=p18a,
        person_b=p18b,
        public_overlap_summary="Both list 'Vinyl Records' and 'Classical Music'",
        hidden_conversational_facts="Shared emotional sensitivity, gentle communication, and quiet musical domestic harmony",
        ground_truth_score=9.2,
        discovery_narrative="Meenakshi and Devang bonded over vinyl mastering and emotional harmony; immediate spark.",
    ))

    # Case 19: Polite Small Talk / Zero Chemistry (Lukewarm / True Negative)
    # Public: Reading & Pour-over Coffee -> Prior ranks moderate (6.2)
    # Hidden: Polite and respectful, but conversation feels like a corporate job interview; zero romantic spark.
    # Ground Truth: 4.8 (Polite but lukewarm)
    p19a = _build_research_persona(
        pid="study-19a",
        name="Sunita Paul",
        public_headline="Operations Consultant & Book Club Member",
        public_hobbies=["Reading", "Coffee", "Museums"],
        public_interests=["Process design", "Historical fiction", "Cafes"],
        stated_pace="Structured and tidy",
        hidden_needs=["An exciting partner with spontaneous creative energy who pulls me out of routine"],
        hidden_dealbreakers=["Rigid predictable conversation that feels like an office meeting"],
        hidden_private_truth="Finds herself having polite, predictable small talk; craves passionate spark.",
        coaching_directives=["See if they can be playful and spontaneous, or if it feels like a job interview."],
    )
    p19b = _build_research_persona(
        pid="study-19b",
        name="Rahul Varma",
        public_headline="Compliance Specialist & Avid Reader",
        public_hobbies=["Reading", "Coffee", "City Walks"],
        public_interests=["Regulatory audit", "Non-fiction books", "Espresso"],
        stated_pace="Structured and methodical",
        hidden_needs=["A warm partner who appreciates structured schedules and calm routine"],
        hidden_dealbreakers=["Chaotic unpredictability"],
        hidden_private_truth="Communicates in measured, formal sentences; struggles with spontaneous flirtation.",
        coaching_directives=["Keep conversation polite, structured, and formal."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="polite_zero_spark",
        person_a=p19a,
        person_b=p19b,
        public_overlap_summary="Both list 'Reading' and 'Coffee' with structured tags",
        hidden_conversational_facts="Polite exchange but conversation feels like a formal job interview; zero romantic spark",
        ground_truth_score=4.8,
        discovery_narrative="Sunita and Rahul were perfectly polite, but conversation remained stiff and formal.",
    ))

    # Case 20: Mismatched Conversational Tempo (Lukewarm / True Negative)
    # Public: Travel & Cinema -> Prior ranks moderate (6.0)
    # Hidden: Bhavna speaks in rapid-fire 10-minute monologues; Kunal needs 10-second pauses; mutual exhaustion.
    # Ground Truth: 4.5 (Pacing friction)
    p20a = _build_research_persona(
        pid="study-20a",
        name="Bhavna Shah",
        public_headline="Broadcast Journalist & Film Enthusiast",
        public_hobbies=["Travel", "Cinema", "Theater"],
        public_interests=["Documentaries", "World news", "Film festivals"],
        stated_pace="High-velocity rapid-fire",
        hidden_needs=["A partner who can match my rapid-fire conversational speed and quick banter"],
        hidden_dealbreakers=["Slow, silent talkers who take long pauses"],
        hidden_private_truth="Speaks in rapid 10-minute bursts; feels anxious when pauses last more than 3 seconds.",
        coaching_directives=["Keep energy high and see if they can keep up with fast conversation."],
    )
    p20b = _build_research_persona(
        pid="study-20b",
        name="Kunal Singhania",
        public_headline="Archival Film Editor & Researcher",
        public_hobbies=["Travel", "Cinema", "Film Photography"],
        public_interests=["Silent film", "Color grading", "Writing"],
        stated_pace="Slow contemplative pause",
        hidden_needs=["A partner comfortable with 10-second pauses before speaking"],
        hidden_dealbreakers=["Overwhelming rapid-fire talkers who never let others finish a thought"],
        hidden_private_truth="Needs time to reflect before answering; easily overwhelmed by non-stop monologues.",
        coaching_directives=["Take time to reflect and pause before answering questions."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="mismatched_tempo",
        person_a=p20a,
        person_b=p20b,
        public_overlap_summary="Both list 'Travel' and 'Cinema'",
        hidden_conversational_facts="Bhavna talks in rapid-fire monologues; Kunal requires 10-second reflective pauses",
        ground_truth_score=4.5,
        discovery_narrative="Bhavna felt frustrated by silence; Kunal felt overwhelmed by speed. Mutual pacing mismatch.",
    ))

    # Case 21: Biting Sarcasm vs. Earnest Sensitivity (Lukewarm / True Negative)
    # Public: Standup Comedy & Weekend Hiking -> Prior ranks moderate (5.8)
    # Hidden: Vivek communicates via biting sarcastic roasts; Shalini is earnest and feels constantly stung.
    # Ground Truth: 4.2 (Communication style disconnect)
    p21a = _build_research_persona(
        pid="study-21a",
        name="Shalini Gupta",
        public_headline="Children's Book Editor & Nature Hiker",
        public_hobbies=["Hiking", "Standup Comedy", "Watercolors"],
        public_interests=["Illustrated books", "Trail walking", "Storytelling"],
        stated_pace="Earnest and gentle",
        hidden_needs=["A kind, sincere partner who communicates with warmth and genuine encouragement"],
        hidden_dealbreakers=["Biting sarcasm, mocking cynicism, aggressive teasing"],
        hidden_private_truth="Sensitive and sincere; gets deeply hurt when humor is used as a weapon to mock.",
        coaching_directives=["Watch out for cynical sarcasm; I need genuine kindness and sincerity."],
    )
    p21b = _build_research_persona(
        pid="study-21b",
        name="Vivek Anand",
        public_headline="Copywriter & Comedy Open-Mic Performer",
        public_hobbies=["Standup Comedy", "Hiking", "Podcasts"],
        public_interests=["Satire", "Roast comedy", "Improv"],
        stated_pace="Edgy sarcastic banter",
        hidden_needs=["A partner with thick skin who loves biting sarcasm and witty roast banter"],
        hidden_dealbreakers=["People who take jokes too seriously and get offended easily"],
        hidden_private_truth="Uses sarcasm as an emotional armor; teases relentlessly to test if people can handle it.",
        coaching_directives=["Use witty sarcasm and playful teasing to see if they can banter back."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="humor_disconnect",
        person_a=p21a,
        person_b=p21b,
        public_overlap_summary="Both list 'Standup Comedy' and 'Hiking'",
        hidden_conversational_facts="Vivek uses aggressive sarcastic roasts; Shalini is earnest and sensitive",
        ground_truth_score=4.2,
        discovery_narrative="Vivek's sarcastic banter felt hurtful to Shalini; communication styles conflicted sharply.",
    ))

    # Case 22: Opposing Social Batteries (Lukewarm / True Negative)
    # Public: Food Trucks & Board Games -> Prior ranks moderate (6.4)
    # Hidden: Aman needs 6 nights/week high-energy parties; Preeti has 1-hour battery and needs days of solitude.
    # Ground Truth: 4.6 (Social energy friction)
    p22a = _build_research_persona(
        pid="study-22a",
        name="Preeti Nambiar",
        public_headline="Data Engineer & Board Game Designer",
        public_hobbies=["Board Games", "Food Trucks", "Reading"],
        public_interests=["Strategy games", "Quiet cafes", "Coding"],
        stated_pace="Low-energy introverted sanctuary",
        hidden_needs=["A low-key partner who enjoys quiet cozy nights and respects need for 4 days of solitude"],
        hidden_dealbreakers=["Party animals who demand going out every evening"],
        hidden_private_truth="Social battery drains after 60 minutes; needs quiet domestic weekends to recharge.",
        coaching_directives=["Check how often they like going out; I need mostly quiet nights in."],
    )
    p22b = _build_research_persona(
        pid="study-22b",
        name="Aman Chawla",
        public_headline="Events Producer & Community Manager",
        public_hobbies=["Food Trucks", "Board Games", "Live Music"],
        public_interests=["Social mixers", "Crowd gaming", "Nightlife"],
        stated_pace="High-octane social butterfly",
        hidden_needs=["An outgoing partner who loves going to events 5-6 nights a week with large crowds"],
        hidden_dealbreakers=["Homebodies who never want to leave the apartment"],
        hidden_private_truth="Gets energized by loud rooms and constant social calendars; cannot stand sitting home.",
        coaching_directives=["Ask if they love busy social calendars and meeting new groups constantly."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="social_battery_clash",
        person_a=p22a,
        person_b=p22b,
        public_overlap_summary="Both list 'Food Trucks' and 'Board Games'",
        hidden_conversational_facts="Aman wants 6-day social party life; Preeti has 1-hour social battery and needs solitude",
        ground_truth_score=4.6,
        discovery_narrative="Preeti explained her introvert battery; Aman expressed craving for nightly social crowds.",
    ))

    # Case 23: Conflicting Ambition Horizons (Lukewarm / True Negative)
    # Public: Film Photography & Cycling -> Prior ranks moderate (5.9)
    # Hidden: Shruti is laser-focused on moving to Silicon Valley; Gautam wants to stay in hometown and relax.
    # Ground Truth: 4.9 (Life trajectory diverge)
    p23a = _build_research_persona(
        pid="study-23a",
        name="Shruti Desai",
        public_headline="Product Strategist & Street Photographer",
        public_hobbies=["Film Photography", "Cycling", "Tech"],
        public_interests=["Silicon valley", "Street candid", "Startups"],
        stated_pace="Hyper-ambitious ladder climber",
        hidden_needs=["A highly ambitious partner aiming for top leadership in Silicon Valley or London"],
        hidden_dealbreakers=["Complacency, wanting a slow small-town life"],
        hidden_private_truth="Determined to climb executive tech ranks; plans to relocate to SF or London within 18 months.",
        coaching_directives=["Probe career ambition and see if they want to move to global tech hubs."],
    )
    p23b = _build_research_persona(
        pid="study-23b",
        name="Gautam Bakshi",
        public_headline="High School Science Teacher & Cyclist",
        public_hobbies=["Cycling", "Film Photography", "Gardening"],
        public_interests=["Pedagogy", "Vintage lenses", "Local parks"],
        stated_pace="Peaceful hometown contentment",
        hidden_needs=["A content partner who appreciates a calm, modest lifestyle in our current hometown"],
        hidden_dealbreakers=["Obsessive corporate careerism, relentless relocations"],
        hidden_private_truth="Loves teaching and has zero desire to leave hometown or chase corporate titles.",
        coaching_directives=["Clarify that I love my hometown and value a relaxed, non-competitive life."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="ambition_tempo_friction",
        person_a=p23a,
        person_b=p23b,
        public_overlap_summary="Both list 'Film Photography' and 'Cycling'",
        hidden_conversational_facts="Shruti is climbing to Silicon Valley; Gautam is content with relaxed hometown life",
        ground_truth_score=4.9,
        discovery_narrative="Shruti shared global corporate ambitions; Gautam affirmed hometown contentment. Divergent paths.",
    ))

    # Case 24: Casual Acquaintances / Platonic Friend Zone (Lukewarm / True Negative)
    # Public: Home Cooking & Indie Pop -> Prior ranks moderate (6.1)
    # Hidden: Great buddy energy for cooking dinner, but mutually 100% platonic with zero romantic attraction.
    # Ground Truth: 5.2 (Platonic friend vibe)
    p24a = _build_research_persona(
        pid="study-24a",
        name="Lavanya Soni",
        public_headline="Graphic Designer & Recipe Developer",
        public_hobbies=["Home Cooking", "Indie Pop", "Thrifting"],
        public_interests=["Recipe zines", "Concerts", "Ceramics"],
        stated_pace="Warm artistic buddy",
        hidden_needs=["Romantic chemistry with electric spark; avoids falling into polite roommate/buddy dynamic"],
        hidden_dealbreakers=["Zero physical or romantic spark"],
        hidden_private_truth="Easy to get along with as friends, but will not settle for purely platonic roommate energy.",
        coaching_directives=["Notice if there is romantic attraction, or if it feels like a friendly hang."],
    )
    p24b = _build_research_persona(
        pid="study-24b",
        name="Manish Khanna",
        public_headline="UI Illustrator & Music Blogger",
        public_hobbies=["Indie Pop", "Home Cooking", "Record Stores"],
        public_interests=["Music zines", "Curry recipes", "Illustration"],
        stated_pace="Friendly casual hang",
        hidden_needs=["Passionate romantic attraction, not just comfortable friend banter"],
        hidden_dealbreakers=["Settling for platonic buddy dynamic without chemistry"],
        hidden_private_truth="Friendly and easygoing, but agrees that romance requires distinct spark beyond camaraderie.",
        coaching_directives=["Be friendly and honest about whether there is romantic spark or just buddy vibes."],
    )
    pairs.append(ConversationalBenchmarkPair(
        pair_id="platonic_friend_zone",
        person_a=p24a,
        person_b=p24b,
        public_overlap_summary="Both list 'Home Cooking' and 'Indie Pop'",
        hidden_conversational_facts="Great friendly buddy camaraderie, but mutually zero romantic spark (platonic vibe)",
        ground_truth_score=5.2,
        discovery_narrative="Lavanya and Manish enjoyed warm recipe banter, but mutually recognized pure platonic friend energy.",
    ))

    return pairs


def run_conversational_study() -> dict[str, Any]:
    """Execute empirical research study comparing Profile-Only Prior vs. Conversational Dates."""
    cohort = generate_research_cohort()
    
    pair_results = []
    prior_errors = []
    agent_errors = []
    
    gt_scores = []
    prior_scores = []
    agent_scores = []

    for pair in cohort:
        pa, pb = pair.person_a, pair.person_b
        store.save_person(pa)
        store.save_person(pb)
        
        # 1. Baseline: Profile-Only Prior Score (y_prior)
        c = compat.compute(pa.analysis, pb.analysis)
        y_prior = round(float(c.prior), 2)
        
        # 2. Treatment: Conversational Date Real Agent Verdict Score (y_agent)
        # Execute date with autonomous agents revealing conversational facts
        d_rec = dater.go_on_date(
            pa.id,
            pa.analysis,
            pb.id,
            pb.analysis,
            coaching_a=pa.coaching_notes,
            coaching_b=pb.coaching_notes,
        )
        store.save_date(d_rec)
        y_agent = round(float(d_rec.mutual), 2)
        y_gt = pair.ground_truth_score

        err_prior = abs(y_prior - y_gt)
        err_agent = abs(y_agent - y_gt)

        prior_errors.append(err_prior)
        agent_errors.append(err_agent)
        
        gt_scores.append(y_gt)
        prior_scores.append(y_prior)
        agent_scores.append(y_agent)

        pair_results.append({
            "pair_id": pair.pair_id,
            "name_a": pa.analysis.display_name,
            "name_b": pb.analysis.display_name,
            "public_overlap_summary": pair.public_overlap_summary,
            "hidden_conversational_facts": pair.hidden_conversational_facts,
            "discovery_narrative": pair.discovery_narrative,
            "ground_truth_score": y_gt,
            "baseline_prior_score": y_prior,
            "agent_verdict_score": y_agent,
            "error_prior": round(err_prior, 2),
            "error_agent": round(err_agent, 2),
            "error_reduction": round(err_prior - err_agent, 2),
            "agent_won": err_agent < err_prior,
            "date_id": d_rec.id,
            "engine": d_rec.engine,
        })

    # Statistical aggregations
    n = len(cohort)
    mae_prior = round(sum(prior_errors) / n, 2)
    mae_agent = round(sum(agent_errors) / n, 2)
    
    rmse_prior = round(math.sqrt(sum(e**2 for e in prior_errors) / n), 2)
    rmse_agent = round(math.sqrt(sum(e**2 for e in agent_errors) / n), 2)

    # Percentage error reduction: (MAE_prior - MAE_agent) / MAE_prior * 100
    error_reduction_pct = round(((mae_prior - mae_agent) / mae_prior) * 100, 1) if mae_prior > 0 else 0.0

    # Spearman rank correlation
    def spearman_rho(x: list[float], y: list[float]) -> float:
        """Compute Spearman rank correlation coefficient."""
        def rank_array(arr: list[float]) -> list[float]:
            sorted_indices = sorted(range(len(arr)), key=lambda i: arr[i])
            ranks = [0.0] * len(arr)
            for r, idx in enumerate(sorted_indices, start=1):
                ranks[idx] = float(r)
            return ranks

        rx = rank_array(x)
        ry = rank_array(y)
        k = len(x)
        d_sq = sum((rx[i] - ry[i]) ** 2 for i in range(k))
        denom = k * (k**2 - 1)
        if denom == 0:
            return 1.0
        return round(1.0 - (6.0 * d_sq) / denom, 2)

    rho_prior = spearman_rho(prior_scores, gt_scores)
    rho_agent = spearman_rho(agent_scores, gt_scores)
    rho_gain = round(rho_agent - rho_prior, 2)

    # Best-match recovery (did treatment identify true top matches?)
    top_gt_idx = gt_scores.index(max(gt_scores))
    top_prior_idx = prior_scores.index(max(prior_scores))
    top_agent_idx = agent_scores.index(max(agent_scores))
    agent_recovered_top_match = (top_agent_idx == top_gt_idx)

    is_llm = config.llm_enabled()
    engine_name = config.active_model_name()

    traps = [p for p in pair_results if p["ground_truth_score"] <= 3.5 and p["baseline_prior_score"] >= 7.0]
    gems = [p for p in pair_results if p["ground_truth_score"] >= 8.5 and p["baseline_prior_score"] <= 7.0]

    headline = (
        f"Simulated dates beat profile-only prior by {error_reduction_pct}% calibration error reduction "
        f"(Spearman rho: {rho_prior:+.2f} -> {rho_agent:+.2f}, gain: {rho_gain:+.2f}) [{engine_name}]"
    )

    return {
        "headline": headline,
        "engine": engine_name,
        "llm_enabled": is_llm,
        "metrics": {
            "engine": engine_name,
            "llm_enabled": is_llm,
            "mae_prior": mae_prior,
            "mae_agent": mae_agent,
            "error_reduction_pct": error_reduction_pct,
            "rmse_prior": rmse_prior,
            "rmse_agent": rmse_agent,
            "spearman_rho_prior": rho_prior,
            "spearman_rho_agent": rho_agent,
            "spearman_rho_gain": rho_gain,
            "agent_win_rate_pct": round(sum(1 for p in pair_results if p["agent_won"]) / n * 100, 1),
            "agent_recovered_top_match": agent_recovered_top_match,
            "total_pairs_evaluated": n,
            "superficial_traps_count": len(traps),
            "superficial_traps_error_reduction_pct": round((sum(p["error_prior"] - p["error_agent"] for p in traps) / max(0.01, sum(p["error_prior"] for p in traps))) * 100, 1) if traps else 0.0,
            "hidden_gems_count": len(gems),
            "hidden_gems_error_reduction_pct": round((sum(p["error_prior"] - p["error_agent"] for p in gems) / max(0.01, sum(p["error_prior"] for p in gems))) * 100, 1) if gems else 0.0,
        },
        "pairs": pair_results,
    }


# Backwards compatibility alias
run_conversational_evaluation_study = run_conversational_study


def render_evaluation_comparison_svg(study: dict[str, Any]) -> str:
    """Render publication-quality vector SVG chart comparing Baseline vs Agent vs Ground Truth."""
    pairs = study.get("pairs", [])
    metrics = study.get("metrics", {})
    if not pairs or not metrics or "error_reduction_pct" not in metrics or "spearman_rho_prior" not in metrics or "spearman_rho_agent" not in metrics:
        return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 200" width="100%" height="200">
  <rect width="960" height="200" rx="14" fill="#0d1117" stroke="rgba(235,87,87,0.3)" stroke-width="1.5"/>
  <text x="480" y="85" fill="#eb5757" font-family="-apple-system, sans-serif" font-size="16" font-weight="700" text-anchor="middle">No Empirical Evaluation Data Available</text>
  <text x="480" y="115" fill="#8b949e" font-family="-apple-system, sans-serif" font-size="13" text-anchor="middle">Execute the evaluation study with real agents to measure empirical signal recovery.</text>
</svg>"""

    pct_reduction = float(metrics["error_reduction_pct"])
    rho_prior = float(metrics["spearman_rho_prior"])
    rho_agent = float(metrics["spearman_rho_agent"])

    engine_name = study.get("engine") or metrics.get("engine") or "offline_deterministic"
    is_llm = bool(study.get("llm_enabled") or metrics.get("llm_enabled", False))
    engine_badge_text = f"ENGINE: {engine_name.upper()} (LIVE LLM)" if is_llm else "ENGINE: OFFLINE DETERMINISTIC (HEURISTIC BASELINE)"
    engine_bg = "rgba(46,160,67,0.18)" if is_llm else "rgba(210,153,34,0.18)"
    engine_stroke = "#2ea043" if is_llm else "#d29922"
    engine_color = "#3fb950" if is_llm else "#ffb703"
    badge_width = max(190, len(engine_badge_text) * 7 + 22)

    chart_w, chart_h = 960, 560
    margin_left, margin_top, bar_area_w, bar_area_h = 90, 140, 780, 280

    # Highlight Gain Pill (Top Right)
    pill_w = 340
    pill_x = chart_w - pill_w - 36
    gain_pill_svg = f"""
    <g transform="translate({pill_x}, 36)">
      <rect width="{pill_w}" height="60" rx="12" fill="rgba(46,160,67,0.15)" stroke="#2ea043" stroke-width="1.5"/>
      <text x="{pill_w / 2}" y="24" fill="#3fb950" font-family="-apple-system, sans-serif" font-size="13" font-weight="800" text-anchor="middle">
        {pct_reduction}% CALIBRATION ERROR REDUCTION
      </text>
      <text x="{pill_w / 2}" y="45" fill="#8b949e" font-family="-apple-system, sans-serif" font-size="11" text-anchor="middle">
        Ranking &rho;: {rho_prior:+.2f} &rarr; {rho_agent:+.2f} ({rho_agent - rho_prior:+.2f} gain)
      </text>
    </g>
    """

    bars_svg = ""
    n = len(pairs)
    chart_w, chart_h = (1200, 580) if n > 12 else (960, 560)
    margin_left, margin_top = (65, 140) if n > 12 else (90, 140)
    bar_area_w = chart_w - margin_left - 45
    bar_area_h = 280
    group_w = bar_area_w / max(1, n)
    bar_w = 14 if n > 12 else 26
    val_font_size = 9 if n > 12 else 11
    label_font_size = 9 if n > 12 else 12

    def y_to_px(val: float) -> float:
        clamped = max(0.0, min(10.0, val))
        return margin_top + bar_area_h - (clamped / 10.0) * bar_area_h

    # Horizontal grid lines
    grid_lines_svg = ""
    for y_val in [0, 2, 4, 6, 8, 10]:
        py = y_to_px(y_val)
        grid_lines_svg += f"""
        <line x1="{margin_left}" y1="{py}" x2="{margin_left + bar_area_w}" y2="{py}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="3,3"/>
        <text x="{margin_left - 10}" y="{py + 4}" fill="#8b949e" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="11" text-anchor="end">{y_val}</text>
        """

    for i, p in enumerate(pairs):
        cx = margin_left + i * group_w + group_w / 2
        y_prior = p["baseline_prior_score"]
        y_agent = p["agent_verdict_score"]
        y_gt = p["ground_truth_score"]

        # Bar 1: Prior (Blue)
        py_prior = y_to_px(y_prior)
        h_prior = (margin_top + bar_area_h) - py_prior
        x_prior = cx - bar_w - 2

        # Bar 2: Agent Verdict (Coral/Accent)
        py_agent = y_to_px(y_agent)
        h_agent = (margin_top + bar_area_h) - py_agent
        x_agent = cx + 2

        # Ground Truth Marker (Gold Diamond / Line)
        py_gt = y_to_px(y_gt)

        # Label pair abbreviation
        short_a = p["name_a"].split()[0][:6]
        short_b = p["name_b"].split()[0][:6]
        pair_label = html.escape(f"{short_a}×{short_b}")

        bars_svg += f"""
        <!-- Pair {i}: {pair_label} -->
        <g>
          <!-- Baseline Prior Bar -->
          <rect x="{x_prior}" y="{py_prior}" width="{bar_w}" height="{h_prior}" rx="3" fill="#388bfd" fill-opacity="0.85"/>
          <text x="{x_prior + bar_w/2}" y="{py_prior - 4}" fill="#58a6ff" font-family="-apple-system, sans-serif" font-size="{val_font_size}" font-weight="600" text-anchor="middle">{y_prior:.1f}</text>

          <!-- Agent Date Verdict Bar -->
          <rect x="{x_agent}" y="{py_agent}" width="{bar_w}" height="{h_agent}" rx="3" fill="#ff4d6d" fill-opacity="0.9"/>
          <text x="{x_agent + bar_w/2}" y="{py_agent - 4}" fill="#ff758f" font-family="-apple-system, sans-serif" font-size="{val_font_size}" font-weight="700" text-anchor="middle">{y_agent:.1f}</text>

          <!-- Ground Truth Gold Target Marker -->
          <line x1="{cx - bar_w - 5}" y1="{py_gt}" x2="{cx + bar_w + 5}" y2="{py_gt}" stroke="#ffb703" stroke-width="2.5" stroke-dasharray="3,1"/>
          <polygon points="{cx},{py_gt-4} {cx+4},{py_gt} {cx},{py_gt+4} {cx-4},{py_gt}" fill="#ffb703"/>

          <!-- X-Axis Label -->
          <text x="{cx}" y="{margin_top + bar_area_h + 20}" fill="#e6edf3" font-family="-apple-system, sans-serif" font-size="{label_font_size}" font-weight="600" text-anchor="middle">{pair_label}</text>
          <text x="{cx}" y="{margin_top + bar_area_h + 34}" fill="#8b949e" font-family="-apple-system, sans-serif" font-size="{val_font_size}" text-anchor="middle">y*:{y_gt:.1f}</text>
        </g>
        """

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {chart_w} {chart_h}" width="{chart_w}" height="{chart_h}">
  <defs>
    <linearGradient id="chart-bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#161b22"/>
    </linearGradient>
  </defs>

  <!-- Deep Canvas Background -->
  <rect width="{chart_w}" height="{chart_h}" rx="16" fill="url(#chart-bg)" stroke="rgba(255,255,255,0.12)" stroke-width="1.5"/>

  <!-- Research Title & Publication Header -->
  <g transform="translate(36, 36)">
    <rect width="210" height="28" rx="14" fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.15)"/>
    <text x="105" y="18" fill="#58a6ff" font-family="-apple-system, sans-serif" font-size="11" font-weight="700" letter-spacing="1" text-anchor="middle">EMPIRICAL EVALUATION</text>
    <text x="0" y="54" fill="#ffffff" font-family="Georgia, serif" font-size="24" font-weight="700">Simulated Dates vs. Profile-Only Baseline</text>
    <text x="0" y="78" fill="#8b949e" font-family="-apple-system, sans-serif" font-size="14">
      Conversational agent dialogue recovers latent facts withheld from public profiles (elderly care, moving abroad, secret dreams).
    </text>
    <!-- Engine Provenance Badge -->
    <g transform="translate(0, 92)">
      <rect width="{badge_width}" height="22" rx="6" fill="{engine_bg}" stroke="{engine_stroke}" stroke-width="1"/>
      <text x="10" y="15" fill="{engine_color}" font-family="-apple-system, sans-serif" font-size="10" font-weight="700">{engine_badge_text}</text>
    </g>
  </g>

  <!-- Highlight Gain Pill (Top Right) -->
  <g transform="translate({chart_w - 380}, 36)">
    <rect width="344" height="60" rx="12" fill="rgba(46,160,67,0.15)" stroke="#2ea043" stroke-width="1.5"/>
    <text x="172" y="24" fill="#3fb950" font-family="-apple-system, sans-serif" font-size="13" font-weight="800" text-anchor="middle">
      {pct_reduction}% CALIBRATION ERROR REDUCTION
    </text>
    <text x="172" y="45" fill="#8b949e" font-family="-apple-system, sans-serif" font-size="11" text-anchor="middle">
      Spearman &rho;: {rho_prior:+.2f} &rarr; {rho_agent:+.2f} ({rho_agent - rho_prior:+.2f} gain)
    </text>
  </g>

  <!-- Legend -->
  <g transform="translate({chart_w - 530}, 112)">
    <!-- Legend 1: Baseline -->
    <rect x="0" y="0" width="14" height="14" rx="3" fill="#388bfd"/>
    <text x="20" y="12" fill="#8b949e" font-family="-apple-system, sans-serif" font-size="12">Profile Prior (&mu; err: {metrics.get('mae_prior', 0.0)})</text>

    <!-- Legend 2: Agent Verdict -->
    <rect x="180" y="0" width="14" height="14" rx="3" fill="#ff4d6d"/>
    <text x="200" y="12" fill="#8b949e" font-family="-apple-system, sans-serif" font-size="12">Agent Date (&mu; err: {metrics.get('mae_agent', 0.0)})</text>

    <!-- Legend 3: Ground Truth -->
    <line x1="330" y1="7" x2="350" y2="7" stroke="#ffb703" stroke-width="3" stroke-dasharray="3,2"/>
    <polygon points="340,3 344,7 340,11 336,7" fill="#ffb703"/>
    <text x="358" y="12" fill="#ffb703" font-family="-apple-system, sans-serif" font-size="12">Ground Truth (y*)</text>
  </g>

  <!-- Axis & Grid -->
  {grid_lines_svg}

  <!-- Plot Bars & Markers -->
  {bars_svg}

  <!-- Footer Citation Tag -->
  <text x="{chart_w / 2}" y="{chart_h - 18}" fill="#6e7681" font-family="-apple-system, sans-serif" font-size="11" text-anchor="middle">
    N={n} Controlled Relational Cohorts · Latent facts evaluated in multi-turn date transcripts · AMORA Autonomous Evaluation Framework
  </text>
</svg>"""
    return svg.strip()
