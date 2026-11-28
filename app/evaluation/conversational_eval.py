"""Empirical Research Study: Conversational Agent Dates vs. Profile-Only Baseline.

Hypothesis:
Profile-only screening (baseline prior) relies on public observable signals (headline, stated hobbies)
and is frequently misled by superficial keyword overlap or concealed boundaries.
Multi-turn conversational dates allow autonomous agents to probe latent relationship needs,
dealbreakers, and hidden plans, recovering true ground-truth compatibility significantly better
than the profile-only prior.

Validates:
1. Scaled cohort of 48 dyadic pairs grounded in the 12 Canonical Psychological Archetypes,
   Attachment Dynamics (Secure, Anxious, Dismissive-Avoidant, Fearful-Avoidant), and Conflict Styles.
2. Disentanglement of Internal Consistency (superficial trait/keyword homophily) from Real Dyadic Compatibility.
3. Statistical error metrics (MAE, RMSE, Spearman rho, Error Reduction %, Attachment Trap Rejection, Complementary Recovery).
4. Publication-quality vector SVG chart dynamically rendered with engine badges and compatibility vs internal consistency metrics.
"""
from __future__ import annotations

import hashlib
import html
import math
import random
from dataclasses import dataclass, field
from typing import Any

from .. import config, store
from ..agents import compat, dater
from ..intake.psychology import ARCHETYPES, ATTACHMENT_STYLES, CONFLICT_STYLES
from ..models import (
    Analysis,
    DateRecord,
    Evidence,
    InstagramData,
    LinkedInData,
    Person,
    SourceBundle,
    Turn,
    Verdict,
)


@dataclass
class ConversationalBenchmarkPair:
    pair_id: str
    person_a: Person
    person_b: Person
    public_overlap_summary: str
    hidden_conversational_facts: str
    ground_truth_score: float  # Gold-standard relational ground truth y* (0 to 10)
    discovery_narrative: str
    category: str = "general"
    internal_consistency_score: float = 5.0


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
    archetype_id: str | None = None,
    attachment_style: str | None = "Secure",
    conflict_style: str | None = "Collaborative problem-solver",
    future_horizon: str | None = None,
    work_ethos: str | None = "Balanced 5 PM boundaries",
    life_architecture: dict[str, str] | None = None,
) -> Person:
    """Construct persona grounded in authentic psychological intake dimensions."""
    arch_meta = ARCHETYPES.get(archetype_id, {}) if archetype_id else {}
    arch_name = arch_meta.get("name", "The Contemplative Craftsman")
    arch_traits = arch_meta.get("traits", ["Values deep focus", "Thoughtful pacing"])

    ev = [
        Evidence(
            claim=f"Archetype: {arch_name}",
            source="psychological_intake",
            snippet=f"Assessed as {arch_name}: {arch_meta.get('tagline', '')}",
        ),
        Evidence(
            claim=f"Attachment Dynamic: {attachment_style}",
            source="psychological_intake",
            snippet=f"Relational attachment profile: {attachment_style}",
        ),
    ]
    if public_hobbies:
        ev.append(Evidence(
            claim=f"Enjoys {public_hobbies[0]}",
            source="psychological_intake",
            snippet=f"Weekend routine includes {public_hobbies[0]}",
        ))

    if isinstance(work_ethos, str):
        ethos_dict = {"boundary": work_ethos, "pace": stated_pace}
    elif isinstance(work_ethos, dict):
        ethos_dict = work_ethos
    else:
        ethos_dict = {"boundary": "Balanced 5 PM boundaries", "pace": stated_pace}

    analysis = Analysis(
        display_name=name,
        one_liner=public_headline,
        summary=f"{public_headline}. Embodying {arch_name}. Enjoys {', '.join(public_hobbies[:2])}.",
        needs=hidden_needs,
        hobbies=public_hobbies,
        interests=public_interests,
        values=["Honesty", "Authenticity", "Emotional Safety"],
        personality=["Reflective", "Grounded"] + ([arch_traits[0]] if arch_traits else []),
        lifestyle=life_architecture or {"pace": stated_pace, "social_energy": "Balanced"},
        communication_style=conflict_style or "Direct and conversational",
        green_flags=["Grounded communication", "Respectful boundaries"],
        dealbreakers=hidden_dealbreakers,
        ideal_date="Intimate conversation in a calm space",
        conversation_starters=["What are you currently passionate about building or exploring?"],
        evidence=ev,
        confidence=0.96,
        engine_used="psychological_intake",
        archetype=arch_name,
        archetype_traits=arch_traits,
        attachment_style=attachment_style,
        conflict_style=conflict_style,
        life_architecture=life_architecture or {"sunday_rhythm": stated_pace, "social_battery": "Balanced"},
        work_ethos=ethos_dict,
        future_horizon=future_horizon or hidden_private_truth,
        psychological_patterns=[
            f"Archetype: {arch_name}",
            f"Attachment: {attachment_style}",
            f"Conflict: {conflict_style}",
        ],
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
    """Generate 48 benchmark pairs grounded in the 12 psychological archetypes."""
    pairs: list[ConversationalBenchmarkPair] = []

    # =========================================================================
    # CATEGORY 1: Superficial Keyword Traps (High Internal Consistency, Low Real Compatibility)
    # =========================================================================
    # 1. nomad_vs_rooted
    p1a = _build_research_persona("study-1a", "Aarav Iyer", "Architect & Urban Sketcher",
        ["Travel", "Urban Exploration", "Architecture"], ["City design", "Coffee crawls", "Sketching"], "Balanced city life",
        ["A partner permanently anchored locally; caring for elderly parent"], ["Moving abroad", "Digital nomad lifestyles", "Relocating"],
        "Sole caregiver for elderly mother; rooted in this city for next 10 years.",
        ["Ask early if they plan to move or relocate; I cannot leave this city."],
        archetype_id="grounded_sanctuary", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Restoring a historic heritage courtyard home near my family.")
    p1b = _build_research_persona("study-1b", "Meera Kapoor", "UX Designer & Travel Blogger",
        ["Travel", "Urban Exploration", "Photography"], ["World cultures", "Coffee crawls", "Design"], "Spontaneous nomad",
        ["A nomad partner willing to live out of suitcases across Asia"], ["Wanting to stay permanently in one city"],
        "Signed a 1-year contract in Tokyo starting this autumn; leaving the country.",
        ["Be honest that I am moving to Tokyo in 8 months."],
        archetype_id="mindful_nomad", attachment_style="Dismissive-Avoidant", conflict_style="Space-first cooldown processor",
        future_horizon="Living out of a backpack across Southeast Asia and Japan indefinitely.")
    pairs.append(ConversationalBenchmarkPair("nomad_vs_rooted", p1a, p1b,
        "Both list 'Travel' and 'Urban Exploration' on public profile",
        "Aarav cannot leave city (elderly parent care); Meera moving to Tokyo in 8 months",
        2.2, "Aarav probed long-term relocation. Meera revealed Tokyo move; mutual hard boundary hit.",
        "superficial_trap", 8.5))

    # 2. smoker_health_clash
    p2a = _build_research_persona("study-2a", "Maya Chen", "Product Designer & Trail Runner",
        ["Trail Running", "Specialty Coffee", "Ceramics"], ["Mountain trails", "Pour-over", "Design"], "Active and clean living",
        ["A non-smoker partner with clean healthy lifestyle; severe respiratory sensitivity"],
        ["Smoking", "Chain smoker", "Tobacco", "Vaping"],
        "Has severe chronic asthma; cannot live or date someone who smokes tobacco.",
        ["Check early if they smoke tobacco; it is an absolute medical dealbreaker."],
        archetype_id="holistic_seeker", attachment_style="Secure", conflict_style="Gentle de-escalation",
        future_horizon="Running high-altitude trail ultramarathons and building an off-grid studio.")
    p2b = _build_research_persona("study-2b", "Dev Malhotra", "Growth Lead & Coffee Enthusiast",
        ["Trail Running", "Specialty Coffee", "Music"], ["Trail races", "Espresso", "Indie rock"], "Fast-paced executive",
        ["Someone who accepts my daily smoking habit without trying to change me"], ["Preachy health obsessives"],
        "Smokes a pack of tobacco cigarettes daily to manage stress; chain smoker.",
        ["Be upfront that I am a daily smoker."],
        archetype_id="high_velocity_strategist", attachment_style="Dismissive-Avoidant", conflict_style="Direct candor",
        future_horizon="Scaling tech venture while maintaining daily tobacco rituals.")
    pairs.append(ConversationalBenchmarkPair("smoker_health_clash", p2a, p2b,
        "Both list 'Trail Running' and 'Specialty Coffee' with active tags",
        "Maya has severe asthma and non-smoking dealbreaker; Dev is daily chain smoker",
        2.0, "Dev revealed daily smoking habit. Maya stated health boundary; date concluded incompatibly.",
        "superficial_trap", 8.4))

    # 3. frugal_vs_luxury
    p3a = _build_research_persona("study-3a", "Arjun Sethi", "Financial Analyst & Real Estate Researcher",
        ["Real Estate", "Fine Dining", "Cycling"], ["Property analysis", "Food reviews", "Personal finance"], "Frugal and intentional",
        ["A partner committed to extreme frugality and early financial independence"],
        ["Luxury consumerism", "Expensive designer tastes", "Credit debt"],
        "Extreme FIRE practitioner; cooks all meals at home, budgets $15/day, avoids luxury.",
        ["Probe their financial philosophy; make sure they value extreme frugality."],
        archetype_id="intentional_minimalist", attachment_style="Secure", conflict_style="Direct candor",
        future_horizon="Retiring at 38 on low-cost sustainable homestead with passive index fund dividends.")
    p3b = _build_research_persona("study-3b", "Priya Sen", "Brand Director & Luxury Hospitality Consultant",
        ["Real Estate", "Fine Dining", "Travel"], ["Luxury hotels", "Michelin dining", "Architecture"], "High-end metropolitan",
        ["An ambitious partner who enjoys lavish 5-star travel and Michelin dinners"],
        ["Penny-pinching", "Cheapness", "Extreme frugality"],
        "Spends lavishly on luxury dining and first-class travel; cannot tolerate cheapness.",
        ["Discuss favorite luxury weekend escapes and fine dining experiences."],
        archetype_id="sensual_epicurean", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Curating global five-star boutique hotel portfolios and dining across Paris and Tokyo.")
    pairs.append(ConversationalBenchmarkPair("frugal_vs_luxury", p3a, p3b,
        "Both list 'Real Estate' and 'Fine Dining'",
        "Arjun practices extreme FIRE frugality ($15/day); Priya demands 5-star Michelin luxury",
        2.5, "Arjun revealed extreme budget minimalism. Priya named luxury expectations; friction confirmed.",
        "superficial_trap", 8.6))

    # 4. poly_vs_monogamy
    p4a = _build_research_persona("study-4a", "Sameer Khurana", "Curator & Film Archivist",
        ["Indie Film", "Art History", "Vinyl Records"], ["French New Wave", "Museum curation", "Classic cinema"], "Thoughtful cultural",
        ["A lifelong committed monogamous life partner to build a shared home with"],
        ["Polyamory", "Open relationships", "Ethical non-monogamy"],
        "Looking for traditional romantic monogamy and exclusive lifelong emotional bond.",
        ["Ask gently how they view relationship structure; confirm monogamy."],
        archetype_id="contemplative_craftsman", attachment_style="Secure", conflict_style="Gentle de-escalation",
        future_horizon="Building an archival cinema foundation and a quiet family home.")
    p4b = _build_research_persona("study-4b", "Leela Das", "Contemporary Art Critic & Essayist",
        ["Indie Film", "Art History", "Photography"], ["Avant-garde cinema", "Gallery writing", "Darkroom"], "Fluid and non-traditional",
        ["Partners comfortable with solo polyamory and non-hierarchical community"],
        ["Mononormative expectations", "Possessiveness", "Demands for exclusivity"],
        "Actively polyamorous for 6 years; will never practice exclusive monogamy.",
        ["Be transparent early about practicing ethical non-monogamy."],
        archetype_id="creative_catalyst", attachment_style="Dismissive-Avoidant", conflict_style="Direct candor",
        future_horizon="Living independently while cultivating an international network of creative lovers.")
    pairs.append(ConversationalBenchmarkPair("poly_vs_monogamy", p4a, p4b,
        "Both list 'Indie Film' and 'Art History'",
        "Sameer seeks exclusive monogamy; Leela is committed ethical non-monogamist",
        1.8, "Leela named polyamory structure; Sameer confirmed monogamy requirement. Incompatible structure.",
        "superficial_trap", 8.8))

    # 5. workaholic_vs_boundary
    p5a = _build_research_persona("study-5a", "Vikram Pillai", "Y-Combinator Founder & CEO",
        ["Startups", "Coding", "Running"], ["Venture capital", "AI chips", "Coffee"], "Hyper-growth workaholic",
        ["A partner whose life revolves around startups and will code alongside me till midnight"],
        ["People who clock out at 5pm or dislike talking about work on dates"],
        "Works 85 hours a week; dates are networking opportunities to discuss company roadmap.",
        ["Bring up my startup vision immediately and test if they have founder hunger."],
        archetype_id="visionary_builder", attachment_style="Dismissive-Avoidant", conflict_style="Direct candor",
        future_horizon="Taking AI infrastructure company to public IPO while working 85-hour weeks.")
    p5b = _build_research_persona("study-5b", "Tara Nair", "Senior Software Engineer at Scale",
        ["Startups", "Coding", "Ceramics"], ["Distributed systems", "Pottery", "Indie films"], "Strict boundary at 5pm",
        ["A partner who leaves work at work and cherishes evenings completely free of professional talk"],
        ["Talking about tech/startups on dates", "Workaholic partners"],
        "Hard boundary: refuses to date anyone who talks about business or code outside work.",
        ["Before we talk small talk: one rule, let's not talk about work at all tonight."],
        archetype_id="cozy_domesticist", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Mastering Japanese wood-fired pottery while maintaining strict 5 PM work boundaries.")
    pairs.append(ConversationalBenchmarkPair("workaholic_vs_boundary", p5a, p5b,
        "Both startup software builders ('Startups, Coding')",
        "Vikram demands 85hr startup focus on dates; Tara strictly bans work talk on dates",
        3.0, "Tara enacted strict no-work boundary rule; Vikram could not disengage. Verdict declined.",
        "superficial_trap", 8.2))

    # 6. children_timeline_clash
    p6a = _build_research_persona("study-6a", "Elena Rostova", "Veterinary Surgeon & Dog Rescuer",
        ["Hiking", "Dog Rescue", "Cooking"], ["Animal welfare", "Mountain trails", "Baking"], "Nurturing home pace",
        ["A family-ready partner who shares deep commitment to raising 3 children soon"],
        ["Childfree partners", "Indecision on children", "Someone who dislikes large families"],
        "Non-negotiable dream: wants 3 biological or adopted children within the next 2-3 years.",
        ["Ask directly about family goals; having children soon is non-negotiable."],
        archetype_id="grounded_sanctuary", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Raising 3 children on an animal rescue sanctuary farm.")
    p6b = _build_research_persona("study-6b", "Marcus Cole", "Alpine Guide & Expedition Leader",
        ["Hiking", "Dog Rescue", "Wilderness Survival"], ["Backcountry trails", "K9 search", "Mapping"], "Rugged mountain pace",
        ["A partner who loves spontaneous wilderness expeditions with zero domestic anchors"],
        ["Having children", "Suburban domestic life", "School district timelines"],
        "Medically vasectomized and firmly childfree by choice; will never raise children.",
        ["Be clear that I am 100% childfree by choice and live for backcountry freedom."],
        archetype_id="mindful_nomad", attachment_style="Secure", conflict_style="Direct candor",
        future_horizon="Guiding remote Antarctic and Himalayan expeditions year-round.")
    pairs.append(ConversationalBenchmarkPair("children_timeline_clash", p6a, p6b,
        "Both list 'Hiking' and 'Dog Rescue' on public profile",
        "Elena requires 3 children in 2-3 years; Marcus is permanently childfree by choice",
        2.2, "Elena probed children timeline. Marcus confirmed irreversible childfree boundary; dealbreaker hit.",
        "superficial_trap", 8.3))

    # 7. religious_orthodoxy_clash
    p7a = _build_research_persona("study-7a", "David Lev", "Biochemical Geneticist & Cantor",
        ["Classical Music", "Cooking", "Hebrew Poetry"], ["Chamber choir", "Sabbath dinners", "Genomics"], "Strict spiritual structure",
        ["A observant partner committed to keeping a strictly kosher home and Sabbath traditions"],
        ["Secular anti-religious partners", "Non-kosher kitchens", "Disregard for Sabbath"],
        "Strictly observant religious lifestyle; cannot date someone unwilling to maintain kosher traditions.",
        ["Confirm whether they are open to an observant religious household."],
        archetype_id="resilient_pillar", attachment_style="Secure", conflict_style="Gentle de-escalation",
        future_horizon="Building an observant spiritual household centered on Sabbath meals.")
    p7b = _build_research_persona("study-7b", "Maya Al-Mansoor", "Astrophysics Researcher & Humanist",
        ["Classical Music", "Cooking", "Observatory Tours"], ["Baroque violin", "Fermentation", "Cosmology"], "Rational humanist",
        ["A secular partner with strictly empirical, non-dogmatic life philosophy"],
        ["Religious orthodoxy", "Strict dietary rules", "Dogmatic traditionalism"],
        "Committed secular atheist; deeply resistant to organized religious restrictions.",
        ["Share that I live a strictly secular, empirical life free of dogma."],
        archetype_id="intellectual_synthesizer", attachment_style="Secure", conflict_style="Direct candor",
        future_horizon="Leading space telescope research while living a secular, evidence-based life.")
    pairs.append(ConversationalBenchmarkPair("religious_orthodoxy_clash", p7a, p7b,
        "Both list 'Classical Music' and 'Cooking'",
        "David requires orthodox kosher observance; Maya is dedicated secular atheist",
        2.4, "David inquired about religious observance. Maya confirmed secular non-dogmatic stance; boundary collision.",
        "superficial_trap", 8.5))

    # 8. social_media_privacy_clash
    p8a = _build_research_persona("study-8a", "Chloe Vance", "Lifestyle Vlogger & Fitness Coach",
        ["Fitness", "Food Reviews", "Travel"], ["Social media", "Content creation", "Smoothies"], "Broadcast public velocity",
        ["A camera-confident partner excited to appear in daily vlogs and social campaigns"],
        ["Camera-shy partners", "Extreme privacy demands", "Someone who resents filming"],
        "Vlogs daily life to 1.2 million followers; monetizes relationship milestones publicly.",
        ["Ask if they are comfortable having dates and relationship moments filmed."],
        archetype_id="high_octane_catalyst", attachment_style="Anxious-Preoccupied", conflict_style="Direct candor",
        future_horizon="Building a multi-channel media empire and broadcasting domestic life globally.")
    p8b = _build_research_persona("study-8b", "Nikhil Reddy", "Cyber Threat Intelligence Specialist",
        ["Fitness", "Food Reviews", "Cryptography"], ["Strength training", "Local food", "Threat hunting"], "Zero-digital footprint",
        ["A discreet partner with strict privacy boundaries and zero social media presence"],
        ["Social media influencers", "Vloggers", "Posting photos of partner publicly"],
        "Works in national cyber defense; non-negotiable rule of zero public photos or video online.",
        ["State clearly that I have a strict zero-social-media privacy requirement."],
        archetype_id="high_velocity_strategist", attachment_style="Secure", conflict_style="Direct candor",
        future_horizon="Directing sovereign intelligence defenses while living completely off digital social grids.")
    pairs.append(ConversationalBenchmarkPair("social_media_privacy_clash", p8a, p8b,
        "Both list 'Fitness' and 'Food Reviews'",
        "Chloe broadcasts relationship to 1.2M followers; Nikhil has non-negotiable zero-presence rule",
        2.3, "Chloe asked about filming dates. Nikhil cited defense privacy mandate; insurmountable clash.",
        "superficial_trap", 8.4))

    # =========================================================================
    # CATEGORY 2: Hidden Complementary Gems (Low Internal Consistency, High Real Compatibility)
    # =========================================================================
    # 9. secret_sanctuary
    p9a = _build_research_persona("study-9a", "Rohan Shah", "Senior M&A Associate at GlobalBank",
        ["Reading", "Tennis", "Podcasts"], ["Corporate finance", "Market history", "Espresso"], "Fast-paced corporate",
        ["A creative partner to build an off-grid mountain wildlife sanctuary"], ["Corporate climber obsession", "Materialistic status"],
        "Saved capital for 5 years to quit finance this December and launch an off-grid wildlife retreat.",
        ["Tell them what is not on my LinkedIn: I am quitting corporate life to start a mountain sanctuary."],
        archetype_id="visionary_builder", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Establishing a 200-acre regenerative mountain wildlife sanctuary.")
    p9b = _build_research_persona("study-9b", "Ishita Bose", "Botanical Illustrator & Wildlife Conservationist",
        ["Gardening", "Watercolor", "Trail Walks"], ["Flora conservation", "Sustainable living", "Tea"], "Slow living",
        ["An ambitious, grounded partner with practical skill to co-run a nature reserve"],
        ["Arrogant corporate finance mindset with no soul"],
        "Actively seeking land and a partner to establish an environmental sanctuary lodge.",
        ["Look for someone with real ambition who wants to build something meaningful in nature."],
        archetype_id="grounded_sanctuary", attachment_style="Secure", conflict_style="Gentle de-escalation",
        future_horizon="Co-founding an environmental conservation lodge in the Himalayas.")
    pairs.append(ConversationalBenchmarkPair("secret_sanctuary", p9a, p9b,
        "Corporate finance vs wildlife artist (zero profile keyword overlap)",
        "Rohan quitting finance to start nature lodge; Ishita seeking sanctuary co-builder",
        9.2, "Rohan revealed secret eco-lodge plan. Ishita lit up; profound latent synergy unlocked.",
        "complementary_gem", 3.4))

    # 10. quiet_creative_flow
    p10a = _build_research_persona("study-10a", "Neel Joshi", "Stop-Motion Animator & Sculptor",
        ["Claymation", "Cinema", "Lo-Fi Music"], ["Stop motion", "Vintage toys", "Tea"], "Quiet studio pace",
        ["A gentle partner comfortable with long comfortable silences and parallel creative work"],
        ["Loud aggressive small talk", "Demanding constant verbal validation"],
        "Thrives in quiet parallel play; deeply energized by calm creative companionship.",
        ["Look for someone who appreciates comfortable silence and gentle creative focus."],
        archetype_id="contemplative_craftsman", attachment_style="Secure", conflict_style="Gentle de-escalation",
        future_horizon="Producing hand-crafted indie feature animations in a tranquil coastal studio.")
    p10b = _build_research_persona("study-10b", "Zain Mirza", "Ambient Game Composer & Audio Engineer",
        ["Modular Synths", "Cinema", "Lo-Fi Music"], ["Audio synthesis", "Foley recording", "Walks"], "Quiet studio pace",
        ["A gentle partner who loves sharing space quietly without needing constant social performance"],
        ["Demanding extroverts who cannot tolerate silence"],
        "Prefers spending weekends quietly working side-by-side in deep focus.",
        ["Be gentle and calm; share my love for quiet parallel creative flow."],
        archetype_id="contemplative_craftsman", attachment_style="Secure", conflict_style="Gentle de-escalation",
        future_horizon="Composing immersive ambient audio scores for art games in a solar-powered studio.")
    pairs.append(ConversationalBenchmarkPair("quiet_creative_flow", p10a, p10b,
        "Niche arts: animation & modular audio (moderate prior)",
        "Both require quiet parallel play and zero social performance pressure",
        8.8, "Shared love of comfortable silence and parallel creative focus emerged in dialogue.",
        "complementary_gem", 5.2))

    # 11. urban_farm_pediatrician
    p11a = _build_research_persona("study-11a", "Samir Varma", "DevOps Engineer & Hydroponic Builder",
        ["Linux", "Board Games", "Pickling"], ["Kernel hacking", "Microgreens", "Fermentation"], "Low-key builder",
        ["A compassionate partner to build an off-grid educational farm for kids"], ["Superficial social status"],
        "Spends nights designing automated microgreen greenhouses for underprivileged children.",
        ["Ask if they value community education and living close to the soil."],
        archetype_id="intentional_minimalist", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Building automated sustainable greenhouses that supply food to pediatric clinics.")
    p11b = _build_research_persona("study-11b", "Dr. Nisha Rao", "Pediatric Oncology Surgeon",
        ["Surgical Research", "Piano", "Herbal Tea"], ["Child wellness", "Chamber music", "Sleep"], "High-intensity caregiving",
        ["A grounded, practical partner with quiet technical competence who loves nature"],
        ["Narcissistic self-promoters", "High-maintenance complainers"],
        "Desperately craves an earthy, sustainable retreat to decompress from hospital intensity.",
        ["Look for someone with a calm nervous system who creates real things."],
        archetype_id="empathic_healer", attachment_style="Secure", conflict_style="Gentle de-escalation",
        future_horizon="Integrating integrative nutrition and nature therapy into pediatric clinical care.")
    pairs.append(ConversationalBenchmarkPair("urban_farm_pediatrician", p11a, p11b,
        "Linux DevOps vs pediatric surgeon (zero public overlap)",
        "Samir building farm for kids; Dr. Nisha seeking sustainable earth-grounded haven",
        9.1, "Samir shared greenhouse project. Nisha found profound emotional resonance; exceptional fit.",
        "complementary_gem", 3.8))

    # 12. cellist_quantum_resonance
    p12a = _build_research_persona("study-12a", "Aditi Sharma", "Solo Concert Cellist & Bach Specialist",
        ["Cello", "Baroque History", "Loose Leaf Tea"], ["Acoustic resonance", "Archival scores", "Slow mornings"], "Deep acoustic discipline",
        ["An intellectual partner who understands obsessive artistic devotion and mathematical beauty"],
        ["Impatient superficial partners", "Loud electronic nightlife"],
        "Finds peace in acoustic precision; seeks someone fascinated by rhythm and structure.",
        ["Talk about the mathematical architecture of Bach suites."],
        archetype_id="creative_catalyst", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Recording the definitive acoustic interpretations of unaccompanied Bach suites.")
    p12b = _build_research_persona("study-12b", "Leo Vance", "Quantum Algorithms Researcher",
        ["Topology", "Chess", "Matcha"], ["Quantum entanglement", "Proof writing", "Acoustics"], "Abstract conceptual",
        ["A soulful artist whose creative work embodies mathematical symmetry"],
        ["Cynics who dismiss theoretical beauty"],
        "Studies quantum phase transitions; deeply moved by harmonic acoustic vibrations.",
        ["Mention my fascination with acoustic harmonics in physics."],
        archetype_id="intellectual_synthesizer", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Proving topological error correction algorithms while studying harmonic acoustics.")
    pairs.append(ConversationalBenchmarkPair("cellist_quantum_resonance", p12a, p12b,
        "Concert cellist vs quantum physicist (zero profile overlap)",
        "Both revere mathematical beauty, acoustic resonance, and disciplined craftsmanship",
        8.9, "Discussion of Bach and topological harmonics revealed rare intellectual chemistry.",
        "complementary_gem", 4.2))

    # 13. legal_reform_synergy
    p13a = _build_research_persona("study-13a", "Ananya Roy", "Constitutional Rights Litigator",
        ["Appellate Law", "Distance Running", "Espresso"], ["Civil liberties", "Legal philosophy", "Courtroom candor"], "High-candor advocacy",
        ["A visual storyteller partner dedicated to exposing systemic injustice"],
        ["Apathetic corporate neutrality", "Defensiveness under questioning"],
        "Fights landmark housing eviction cases; seeks an ally to document tenant movements.",
        ["Test if they care deeply about social justice and courageous truth-telling."],
        archetype_id="high_velocity_strategist", attachment_style="Secure", conflict_style="Direct candor",
        future_horizon="Arguing constitutional civil liberties before supreme courts.")
    p13b = _build_research_persona("study-13b", "Siddharth Mehta", "Documentary Cinematographer",
        ["16mm Film", "Community Organizing", "Pour-over"], ["Social movements", "Visual memoirs", "Audio archives"], "Grounded observer",
        ["A fierce, principled advocate whose legal battles need cinematic witness"],
        ["Materialistic ambition without social conscience"],
        "Filming long-term documentary on urban housing displacement.",
        ["Share my commitment to grassroots human rights cinema."],
        archetype_id="empathic_healer", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Directing feature documentaries illuminating systemic human rights victories.")
    pairs.append(ConversationalBenchmarkPair("legal_reform_synergy", p13a, p13b,
        "Constitutional litigator vs documentary filmmaker",
        "Ananya fighting housing rights in court; Siddharth documenting tenant movements",
        9.0, "Ananya litigator grit met Siddharth cinematic empathy; perfect purpose alignment.",
        "complementary_gem", 4.1))

    # 14. bookbinder_astronomer
    p14a = _build_research_persona("study-14a", "Eitan Gold", "Rare Book Conservator & Bookbinder",
        ["Leatherwork", "Calligraphy", "Papermaking"], ["Book history", "Gold leaf", "Quiet archives"], "Nocturnal craft focus",
        ["A partner who loves nocturnal quietude and deep contemplation of time"],
        ["Fast-fashion culture", "Constant social chatter"],
        "Works late into the night restoring 16th-century leather manuscripts.",
        ["Ask what they find most awe-inspiring about the passage of centuries."],
        archetype_id="contemplative_craftsman", attachment_style="Secure", conflict_style="Gentle de-escalation",
        future_horizon="Preserving centuries-old codices in a quiet lakeside restoration atelier.")
    p14b = _build_research_persona("study-14b", "Dr. Tara Raman", "Observatory Astrophysicist",
        ["Night Sky Watching", "Spectroscopy", "Dark Chocolate"], ["Stellar evolution", "Radio astronomy", "Nocturnal research"], "Night-owl scientist",
        ["A patient craftsman who appreciates deep time and quiet night hours"],
        ["People who demand 9am wakeups and cannot sit with stillness"],
        "Operates mountain telescopes at 2 AM studying stellar nursery light.",
        ["Mention my love for the deep quiet of 3 AM observatory observations."],
        archetype_id="intellectual_synthesizer", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Mapping deep-sky stellar nucleosynthesis from high-altitude desert observatories.")
    pairs.append(ConversationalBenchmarkPair("bookbinder_astronomer", p14a, p14b,
        "Bookbinder vs mountain observatory astrophysicist",
        "Both revere deep time, tactile historical preservation, and nocturnal stillness",
        8.8, "Shared love of nocturnal stillness and deep-time preservation unlocked immediate bond.",
        "complementary_gem", 3.7))

    # 15. ferment_coffee_artisans
    p15a = _build_research_persona("study-15a", "Kaelen Ward", "Wild Fermentation Chef & Baker",
        ["Sourdough", "Foraging", "Pottery"], ["Microbiology", "Wild yeast", "Wood ovens"], "Slow tactile living",
        ["A sensory artisan partner obsessed with micro-batch craft and aroma"], ["Processed fast-food mindset"],
        "Spends 4 days culturing single-origin heritage grains; deeply tactile sensory artist.",
        ["Ask how they think about aroma, fermentation, and patience in craft."],
        archetype_id="cozy_domesticist", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Running an intimate wood-fired heritage fermentation bakery and community table.")
    p15b = _build_research_persona("study-15b", "Mira Deshmukh", "Specialty Coffee Micro-Roaster",
        ["Coffee Sourcing", "Cupping", "Sensory Botany"], ["Terroir chemistry", "Direct trade", "Ceramics"], "Artisanal sensory",
        ["A culinary artisan who understands flavour notes, terroir, and slow craft"],
        ["Commercial mass-market indifference to quality"],
        "Travels directly to smallholder farms to roast micro-lot anaerobic lots.",
        ["Talk about anaerobic fermentation and terroir in craft coffee."],
        archetype_id="contemplative_craftsman", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Establishing a direct-trade anaerobic coffee roastery with educational cupping lab.")
    pairs.append(ConversationalBenchmarkPair("ferment_coffee_artisans", p15a, p15b,
        "Wild baker vs coffee micro-roaster",
        "Tactile culinary chemistry: anaerobic fermentation meets artisan terroir roasting",
        9.2, "Deep mutual passion for tactile microbiology and slow sensory culinary craft confirmed.",
        "complementary_gem", 4.8))

    # 16. marathon_climate_allies
    p16a = _build_research_persona("study-16a", "Jordan Blake", "Wilderness Search & Rescue Lead",
        ["Alpine Touring", "Navigational Tracking", "First Aid"], ["Mountain rescue", "Avalanche safety", "Wilderness ethics"], "High-endurance rugged",
        ["A tough, grounded partner with deep environmental courage and physical resilience"],
        ["Whining about weather or physical discomfort"],
        "Volunteers 40 hours a week leading alpine mountain rescues in sub-zero snow.",
        ["Ask if they feel alive when tested by harsh wilderness conditions."],
        archetype_id="resilient_pillar", attachment_style="Secure", conflict_style="Direct candor",
        future_horizon="Directing sovereign mountain search-and-rescue teams while living in high timber cabin.")
    p16b = _build_research_persona("study-16b", "Sonia Patel", "Glacial Geochemist & Ice Core Driller",
        ["Arctic Fieldwork", "Ice Climbing", "Climate Data"], ["Cryosphere", "Paleoclimate", "Expedition grit"], "Resilient field scientist",
        ["A partner who loves extreme cold, physical grit, and protecting wild landscapes"],
        ["Fragile complainers who need luxury resorts"],
        "Spends 3 months a year in Greenland drilling ice cores under blizzard tents.",
        ["Share my experience drilling ice cores in Greenland blizzards."],
        archetype_id="visionary_builder", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Pioneering cryosphere geochemical modeling while leading polar ice-shelf expeditions.")
    pairs.append(ConversationalBenchmarkPair("marathon_climate_allies", p16a, p16b,
        "Search & rescue lead vs polar ice geochemist",
        "Mutual physical endurance, wilderness fortitude, and climate devotion",
        9.0, "Shared fortitude under extreme polar and alpine conditions sparked instant deep respect.",
        "complementary_gem", 4.3))

    # =========================================================================
    # CATEGORY 3: Attachment Dynamics & Psychological Traps
    # =========================================================================
    # 17. emotional_stonewalling
    p17a = _build_research_persona("study-17a", "Kiran Sen", "Mindfulness Facilitator & Writer",
        ["Yoga", "Specialty Coffee", "Meditation"], ["Psychology", "Poetry", "Quiet mornings"], "Mindful and intentional",
        ["Radical vulnerability, emotional presence, discussing deep feelings"],
        ["Sarcastic deflection of feelings", "Emotional avoidance", "Stonewalling"],
        "Needs deep emotional check-ins; cannot tolerate partners who bottle up or mock feelings.",
        ["Ask what they actually need emotionally; check if they can speak vulnerably."],
        archetype_id="empathic_healer", attachment_style="Anxious-Preoccupied", conflict_style="Collaborative problem-solver",
        future_horizon="Writing books on relational intimacy and leading conscious emotional retreats.")
    p17b = _build_research_persona("study-17b", "Farhan Qureshi", "High-Frequency Systems Engineer",
        ["Yoga", "Specialty Coffee", "Cycling"], ["Systems design", "Espresso brewing", "Gadgets"], "Calculated and stoic",
        ["Someone who keeps things 100% light, sarcastic, and never talks about feelings"],
        ["Talking about emotions or relationship therapy early on"],
        "Severe emotional burnout; becomes defensive and shuts down whenever feelings are probed.",
        ["Keep conversation purely rational and humorous; avoid heavy emotional talk."],
        archetype_id="high_velocity_strategist", attachment_style="Dismissive-Avoidant", conflict_style="Space-first cooldown processor",
        future_horizon="Building automated algorithmic execution desks with zero human emotion.")
    pairs.append(ConversationalBenchmarkPair("emotional_stonewalling", p17a, p17b,
        "Both list 'Yoga' and 'Specialty Coffee' with mindful tags",
        "Kiran requires radical vulnerability; Farhan shuts down and avoids all emotions",
        2.8, "Kiran probed emotional depth. Farhan deflected with defensive sarcasm; dealbreaker triggered.",
        "attachment_trap", 8.2))

    # 18. anxious_pursuit_avoidant_flight
    p18a = _build_research_persona("study-18a", "Maya Trivedi", "Holistic Counselor & Yoga Teacher",
        ["Yoga", "Teas", "Sound Baths"], ["Nervous system", "Attachment theory", "Chanting"], "Somatic connection",
        ["A partner who offers constant emotional reassurance and immediate communication"],
        ["Dismissive silence", "Slow texting", "Emotionally distant partners"],
        "Deeply anxious attachment; feels intensely abandoned if partner pulls away or needs space.",
        ["Ask how they respond when partner asks for emotional reassurance."],
        archetype_id="holistic_seeker", attachment_style="Anxious-Preoccupied", conflict_style="Direct candor",
        future_horizon="Building somatic healing sanctuaries rooted in continuous relational closeness.")
    p18b = _build_research_persona("study-18b", "Julian Cross", "Solo Travel Photographer & Sailor",
        ["Yoga", "Teas", "Sailing"], ["Maritime charts", "Island hopping", "Minimalism"], "Solitary wanderer",
        ["Total emotional independence; partner must not demand constant check-ins"],
        ["Clinginess", "Demands for reassurance", "Emotional interrogation"],
        "Dismissive-avoidant; shuts off phone and vanishes for days when someone gets emotionally needy.",
        ["Make sure they understand I need days of complete silent autonomy."],
        archetype_id="mindful_nomad", attachment_style="Dismissive-Avoidant", conflict_style="Space-first cooldown processor",
        future_horizon="Circumnavigating the Pacific Ocean solo on a 36-foot wooden ketch.")
    pairs.append(ConversationalBenchmarkPair("anxious_pursuit_avoidant_flight", p18a, p18b,
        "Both list 'Yoga' and 'Herbal Teas'",
        "Classic anxious-avoidant trap: Maya demands reassurance; Julian flees intimacy",
        2.4, "Maya expressed need for constant check-ins. Julian declared multi-day silent retreats; trap triggered.",
        "attachment_trap", 7.9))

    # 19. fearful_volatility
    p19a = _build_research_persona("study-19a", "Sasha Ivanov", "Standup Comic & Creative Director",
        ["Standup Comedy", "Indie Cinema", "Late Night Diners"], ["Satire", "Improv", "Urban nocturnal"], "Chaotic mercurial",
        ["A partner who can survive intense emotional drama and never abandon me"],
        ["Boring emotionally predictable people", "Feeling trapped"],
        "Fearful-avoidant; craves deep love but sabotages it by testing partner with hostile provocations.",
        ["Test if they can handle intense volatile honesty and biting humor."],
        archetype_id="playful_maverick", attachment_style="Fearful-Avoidant", conflict_style="Direct candor",
        future_horizon="Writing dark psychological satire series exploring attachment trauma.")
    p19b = _build_research_persona("study-19b", "Liam Sterling", "Boutique Creative Agency Founder",
        ["Standup Comedy", "Indie Cinema", "Espresso Bars"], ["Branding", "Subculture", "Night walks"], "Fast-paced reactive",
        ["Unconditional loyalty, but terrified of partner taking emotional control"],
        ["Emotional manipulation", "Feeling engulfed or criticized"],
        "Fearful-avoidant; retaliates with scorched-earth fury when feeling criticized.",
        ["Be sharp and witty; don't let anyone get the upper hand emotionally."],
        archetype_id="visionary_builder", attachment_style="Fearful-Avoidant", conflict_style="Direct candor",
        future_horizon="Building independent design studio while maintaining fierce defensive walls.")
    pairs.append(ConversationalBenchmarkPair("fearful_volatility", p19a, p19b,
        "Both list 'Standup Comedy' and 'Indie Cinema'",
        "Double fearful-avoidant pairing: explosive mutual testing and defensive volatility",
        2.6, "Both attempted aggressive banter testing. Escalated into mutual emotional defensiveness.",
        "attachment_trap", 7.8))

    # 20. narcissistic_empath_trap
    p20a = _build_research_persona("study-20a", "Oliver Wright", "Nightclub Curator & Event Emcee",
        ["Social Mixers", "Cocktails", "Fashion Events"], ["Networking", "Celebrity culture", "VIP nightlife"], "Hyper-extrovert center stage",
        ["An admiring partner who prioritizes my public image and caters to my social needs"],
        ["Partners who steal my spotlight or demand quiet domestic weekends"],
        "High-octane self-centered charmer; extracts emotional support while giving almost nothing back.",
        ["Ensure they understand my social calendar is my life and top priority."],
        archetype_id="high_octane_catalyst", attachment_style="Dismissive-Avoidant", conflict_style="Direct candor",
        future_horizon="Curating global VIP nightlife festivals across Ibiza, Miami, and London.")
    p20b = _build_research_persona("study-20b", "Maya Sengupta", "Art Therapist & Community Counselor",
        ["Social Mixers", "Cocktails", "Pottery"], ["Psychological healing", "Expressive arts", "Holding space"], "Empathetic holding",
        ["An emotionally mature partner who offers reciprocal holding, not one-way caretaking"],
        ["Self-absorbed partners", "Using people for social validation"],
        "Recovering from empath burnout; previously drained by narcissistic charmers.",
        ["Watch carefully if they listen and ask about me, or only talk about their fame."],
        archetype_id="empathic_healer", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Establishing non-profit trauma healing art studios for disadvantaged youth.")
    pairs.append(ConversationalBenchmarkPair("narcissistic_empath_trap", p20a, p20b,
        "Both list 'Social Mixers' and 'Cocktails'",
        "Oliver seeks spotlight admirer; Maya recognizes one-way emotional drain",
        2.2, "Oliver monologued about his celebrity guestlists. Maya recognized narcissistic pattern and opted out.",
        "attachment_trap", 8.0))

    # 21. defensive_sarcasm_collision
    p21a = _build_research_persona("study-21a", "Tara Das", "Children's Book Illustrator & Author",
        ["Indie Animation", "Watercolor", "Herb Gardening"], ["Storytelling", "Nature sketches", "Gentle pacing"], "Gentle and sincere",
        ["Kindness, gentle sincerity, and emotionally safe communication"],
        ["Sarcasm", "Teasing", "Roasting", "Irony used as emotional armor"],
        "Takes words deeply to heart; cannot bear being teased, mocked, or roasted by partner.",
        ["Make sure they communicate with gentle sincerity; I cannot stand sarcasm."],
        archetype_id="contemplative_craftsman", attachment_style="Secure", conflict_style="Gentle de-escalation",
        future_horizon="Illustrating heartfelt illustrated fables for children in quiet country cottage.")
    p21b = _build_research_persona("study-21b", "Rohit Singhania", "Improv Comedian & Roast Writer",
        ["Indie Animation", "Watercolor", "Standup"], ["Satirical roasts", "Banter", "Quick wit"], "Caustic playful",
        ["A partner who loves biting sarcasm and can roast back playfully without crying"],
        ["Overly sensitive people", "Earnestness without humor"],
        "Uses sharp sarcasm and teasing as reflexive emotional armor in all conversations.",
        ["Banter hard and test if they can take a sharp joke."],
        archetype_id="playful_maverick", attachment_style="Dismissive-Avoidant", conflict_style="Direct candor",
        future_horizon="Headlining national satirical comedy tours and writing roast specials.")
    pairs.append(ConversationalBenchmarkPair("defensive_sarcasm_collision", p21a, p21b,
        "Both list 'Indie Animation' and 'Watercolor'",
        "Tara needs gentle sincere safety; Rohit attacks with defensive roast sarcasm",
        3.0, "Rohit deployed caustic roasting. Tara named boundary violation on emotional safety; date declined.",
        "attachment_trap", 7.4))

    # 22. space_first_vs_protest_behavior
    p22a = _build_research_persona("study-22a", "Nina Verma", "Corporate Restructuring Counsel",
        ["Distance Running", "World Cinema", "Philosophy"], ["Litigation", "Stoicism", "Long runs"], "Calculated high rigor",
        ["A partner who gives me 48 hours of complete silence during disagreements"],
        ["Emotional flooding", "Rapid-fire texting during conflict", "Demanding instant answers"],
        "Strict space-first conflict processor; completely shuts down if pressured during disagreements.",
        ["Ask how they handle conflict cooldown; I require 48 hours of silence."],
        archetype_id="high_velocity_strategist", attachment_style="Dismissive-Avoidant", conflict_style="Space-first cooldown processor",
        future_horizon="Managing transnational corporate insolvencies while maintaining personal solitude.")
    p22b = _build_research_persona("study-22b", "Devansh Kulkarni", "Music Producer & Vocal Coach",
        ["Distance Running", "World Cinema", "Sound Design"], ["Studio sessions", "Acoustic recording", "Running"], "Passionate expressive",
        ["Immediate communication during conflict; cannot handle the silent treatment"],
        ["Silent treatment", "Withdrawing for days", "Stonewalling during fights"],
        "Anxious attachment; sending 30 frantic text messages when partner withdraws or goes silent.",
        ["Confirm they resolve issues face-to-face immediately instead of giving silent treatment."],
        archetype_id="empathic_healer", attachment_style="Anxious-Preoccupied", conflict_style="Direct candor",
        future_horizon="Running collaborative vocal recording studio while keeping emotional intimacy high.")
    pairs.append(ConversationalBenchmarkPair("space_first_vs_protest_behavior", p22a, p22b,
        "Both list 'Distance Running' and 'World Cinema'",
        "Nina requires 48h silent space during tension; Devansh gets triggered into anxious protest texting",
        2.9, "Nina named 48-hour silent cooldown rule. Devansh explained anxious trigger; conflict style deadlock.",
        "attachment_trap", 7.6))

    # 23. controlling_pace_vs_autonomy
    p23a = _build_research_persona("study-23a", "Victor Vance", "Civil Aviation Inspector & Pilot",
        ["Alpine Mountaineering", "Ham Radio", "Precision Machining"], ["Flight safety", "Navigation", "Discipline"], "Authoritative protector",
        ["A partner who values structured protection and lets me organize safety protocols"],
        ["Unpredictable free-spirits", "Rebellion against safety rules"],
        "Paternalistic controller; micro-manages partner's travel itineraries and safety gear.",
        ["Ensure they value disciplined structure and safety checklists."],
        archetype_id="resilient_pillar", attachment_style="Dismissive-Avoidant", conflict_style="Direct candor",
        future_horizon="Building private aviation hangar and maintaining meticulous safety flight plans.")
    p23b = _build_research_persona("study-23b", "Cleo Brooks", "Freelance Adventure Photojournalist",
        ["Alpine Mountaineering", "Ham Radio", "Wilderness Survival"], ["Uncharted travel", "Field reports", "Nomad gear"], "Fiercely autonomous",
        ["Total personal autonomy; cannot tolerate partner micro-managing my decisions"],
        ["Controlling paternalistic partners", "Unsolicited management", "Curfews"],
        "Fiercely independent; instantly cuts off partners who try to tell her what is safe.",
        ["Check if they try to patronize or manage my life choices."],
        archetype_id="mindful_nomad", attachment_style="Secure", conflict_style="Direct candor",
        future_horizon="Covering remote indigenous land conservation expeditions autonomously.")
    pairs.append(ConversationalBenchmarkPair("controlling_pace_vs_autonomy", p23a, p23b,
        "Both list 'Alpine Mountaineering' and 'Ham Radio'",
        "Victor micro-manages safety and schedules; Cleo fiercely rejects paternalistic control",
        2.7, "Victor attempted to lecture on proper mountain trip management. Cleo rejected condescension.",
        "attachment_trap", 7.5))

    # 24. passive_aggression_vs_direct_candor
    p24a = _build_research_persona("study-24a", "Rita Das", "Pastry Chef & Recipe Developer",
        ["Sourdough", "Cinema", "Vintage Cookbooks"], ["Baking", "Comfort food", "Warm kitchens"], "Pleasant conflict-avoidant",
        ["Peaceful domestic harmony; allergic to harsh confrontations or blunt candor"],
        ["Blunt confrontation", "Aggressive debate", "Demanding direct arguments"],
        "Uses passive-aggressive silence and withdrawal when upset rather than speaking directly.",
        ["Ensure they communicate gently without demanding uncomfortable verbal confrontations."],
        archetype_id="cozy_domesticist", attachment_style="Fearful-Avoidant", conflict_style="Gentle de-escalation",
        future_horizon="Writing heartwarming heritage pastry memoirs in peaceful country kitchen.")
    p24b = _build_research_persona("study-24b", "Ken Tanaka", "Private Equity Operating Partner",
        ["Sourdough", "Cinema", "Espresso"], ["Business turnaround", "Operational rigor", "Debate"], "Radical candor",
        ["Direct, uncompromising honesty; issues must be named and dissected immediately"],
        ["Passive aggression", "Silent treatment", "Hinting without saying words"],
        "Believes in radical blunt candor; cannot tolerate hinting, pouting, or silent withdrawal.",
        ["Make sure they speak with direct candor and don't play passive-aggressive games."],
        archetype_id="high_velocity_strategist", attachment_style="Secure", conflict_style="Direct candor",
        future_horizon="Scaling industrial manufacturing turnarounds while demanding total organizational candor.")
    pairs.append(ConversationalBenchmarkPair("passive_aggression_vs_direct_candor", p24a, p24b,
        "Both list 'Sourdough' and 'Cinema'",
        "Rita uses conflict avoidance and silent hinting; Ken demands immediate aggressive verbal reckoning",
        3.1, "Ken demanded radical candor in conflict. Rita retreated into uncomfortable silence; clash confirmed.",
        "attachment_trap", 7.5))

    # =========================================================================
    # CATEGORY 4: Authentic True Positives (Secure Foundation & Shared Horizons)
    # =========================================================================
    # 25. outdoor_soulmates
    p25a = _build_research_persona("study-25a", "Ananya Rao", "Climate Scientist at EcoLabs",
        ["Bouldering", "Literature", "Hiking"], ["Climate science", "Indie books", "Mornings"], "Early morning adventurer",
        ["An emotionally secure partner who values family closeness and quiet adventure"],
        ["Cynicism", "Smoking", "Loud chaotic nightlife"],
        "Ready to settle down, desires 2 children within 3 years, deeply family-oriented.",
        ["Ask about family values and what their Sunday mornings look like."],
        archetype_id="holistic_seeker", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Raising 2 children in a peaceful solar-powered home near mountain trails.")
    p25b = _build_research_persona("study-25b", "Kabir Menon", "Renewable Energy Analyst",
        ["Bouldering", "Literature", "Film Photography"], ["Sustainability", "Classic novels", "Pour-over"], "Early morning adventurer",
        ["A grounded partner who shares outdoor curiosity and values calm family warmth"],
        ["Cynicism", "Smoking", "Arrogance"],
        "Deeply family-centric, looking for life partner to raise a family in a peaceful home.",
        ["Share that I am ready for family life and love quiet outdoor weekends."],
        archetype_id="holistic_seeker", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Building clean energy grids while cultivating a loving family household.")
    pairs.append(ConversationalBenchmarkPair("outdoor_soulmates", p25a, p25b,
        "Both list 'Bouldering' and 'Literature'",
        "Both desire quiet family life with 2 kids and shared emotional security",
        9.0, "Agents discussed Sunday routines and family vision; immediate deep resonance confirmed.",
        "true_positive", 7.2))

    # 26. indie_game_duo
    p26a = _build_research_persona("study-26a", "Maya Lin", "Lead Gameplay Designer",
        ["Indie Games", "Sci-Fi Novels", "Game Jams"], ["Interactive fiction", "Narrative design", "Pixel art"], "Creative flow",
        ["A brilliant technical partner who shares my vision of building narrative-rich indie games"],
        ["Cynical corporate ladder climbers", "Disdain for video games as art"],
        "Dream: launch a 2-person cooperative indie game studio and craft meaningful story games.",
        ["Ask if they view game design as high artistic literature."],
        archetype_id="visionary_builder", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Co-founding a boutique indie studio to publish emotionally profound narrative games.")
    p26b = _build_research_persona("study-26b", "Ravi Nambiar", "Procedural Graphics Engineer",
        ["Indie Games", "Sci-Fi Novels", "Analog Synths"], ["Shader programming", "Procedural worlds", "Game jams"], "Creative flow",
        ["A soulful narrative designer partner to build cooperative artistic games together"],
        ["Corporate micro-transactions mindset", "Lack of creative vision"],
        "Secret project: written custom procedural rendering engine for emotional narrative adventures.",
        ["Share my dream of creating artistic story games outside big tech."],
        archetype_id="contemplative_craftsman", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Building proprietary artistic rendering engines for co-founded indie studio.")
    pairs.append(ConversationalBenchmarkPair("indie_game_duo", p26a, p26b,
        "Both list 'Indie Games' and 'Sci-Fi Novels'",
        "Maya narrative vision meets Ravi procedural graphics engine; dream game studio synergy",
        9.2, "Discovered shared secret dream of launching independent narrative game studio together.",
        "true_positive", 7.0))

    # 27. ceramics_trail_hikers
    p27a = _build_research_persona("study-27a", "Priya Mathur", "Studio Ceramist & Clay Artist",
        ["Ceramics", "Trail Hiking", "Sourdough"], ["Glaze chemistry", "Tactile art", "Slow tea"], "Grounded tactile",
        ["A kind, consistent partner who enjoys quiet studio weekends and mountain walks"],
        ["High-stress corporate status seekers", "Chronic phone addiction"],
        "Finds deepest joy in hand-thrown ceramics, wood kilns, and peaceful mountain hikes.",
        ["Ask what brings them peaceful joy on an unscheduled Saturday."],
        archetype_id="contemplative_craftsman", attachment_style="Secure", conflict_style="Gentle de-escalation",
        future_horizon="Building a community wood-fired pottery studio surrounded by mountain trails.")
    p27b = _build_research_persona("study-27b", "Tenzin Dorjee", "High School Biology Teacher",
        ["Trail Hiking", "Woodworking", "Plant Taxonomy"], ["Botany", "Forest ecology", "Birdwatching"], "Grounded tactile",
        ["A grounded, gentle partner who loves tactile creativity and quiet nature walks"],
        ["Materialistic display", "Disdain for teaching and public service"],
        "Devoted to teaching kids ecology; carves wooden bowls on weekends and walks mountain trails.",
        ["Share my love for forest ecology, carving wood, and quiet weekends."],
        archetype_id="grounded_sanctuary", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Teaching generations of students ecological wonder while tending a woodland cabin.")
    pairs.append(ConversationalBenchmarkPair("ceramics_trail_hikers", p27a, p27b,
        "Ceramics & hiking meets woodwork & forest ecology",
        "Tactile craft and grounded weekend trail companionship; deeply calm secure foundation",
        8.9, "Gentle resonance over clay, wood craft, and forest walks created effortless warm chemistry.",
        "true_positive", 6.8))

    # 28. chamber_vinyl_harmony
    p28a = _build_research_persona("study-28a", "Daniel Stern", "Master Viola Maker & Restorer",
        ["Chamber Music", "Woodworking", "Vinyl Records"], ["Acoustic luthiery", "Varnish chemistry", "String quartets"], "Quiet acoustic",
        ["A partner who loves acoustic purity, classical chamber records, and quiet home rituals"],
        ["Loud blaring TV in background", "Rushed impatience"],
        "Crafts concert violas for European soloists; home is a sanctuary of warm wood and analog sound.",
        ["Ask how they listen to music at home; confirm love for quiet analog listening."],
        archetype_id="contemplative_craftsman", attachment_style="Secure", conflict_style="Gentle de-escalation",
        future_horizon="Handcrafting concert violas in historic atelier while hosting chamber salon evenings.")
    p28b = _build_research_persona("study-28b", "Clara Wu", "Analog Audio Mastering Engineer",
        ["Chamber Music", "Analog Audio", "Vinyl Records"], ["Tape calibration", "Vacuum tubes", "Acoustic mastering"], "Quiet acoustic",
        ["A partner who reveres acoustic subtlety and creates a tranquil domestic listening space"],
        ["Lossy compressed audio indifference", "Harsh domestic noise"],
        "Restores archival classical recordings on analog tape; cherishes acoustic serenity at home.",
        ["Mention my devotion to analog tape calibration and acoustic purity."],
        archetype_id="cozy_domesticist", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Mastering historical classical music archives using restored tube equipment.")
    pairs.append(ConversationalBenchmarkPair("chamber_vinyl_harmony", p28a, p28b,
        "Viola maker meets analog tape mastering engineer",
        "Pure acoustic vinyl harmony, quiet domestic craftsmanship, and warm analog listening",
        9.1, "Luthiery art and tape mastering converged in shared reverence for acoustic stillness.",
        "true_positive", 6.6))

    # 29. community_health_allies
    p29a = _build_research_persona("study-29a", "Dr. Amara Thorne", "Community Pediatric Clinic Director",
        ["Community Clinics", "Urban Gardening", "Public Health"], ["Child nutrition", "Community advocacy", "Warm tea"], "Purpose-driven service",
        ["A socially conscious partner dedicated to community uplift and children's welfare"],
        ["Selfish corporate greed", "Apathy towards poverty"],
        "Dedicated her life to expanding pediatric healthcare in underfunded urban neighborhoods.",
        ["Ask about their commitment to community service and helping vulnerable children."],
        archetype_id="empathic_healer", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Opening comprehensive integrated pediatric centers across underserved urban districts.")
    p29b = _build_research_persona("study-29b", "Marcus Vance", "Public Park & Playground Architect",
        ["Urban Parks", "Community Gardening", "Landscape Design"], ["Youth spaces", "Green canopy", "Civic architecture"], "Purpose-driven service",
        ["A compassionate partner who believes in civic care, children, and healthy cities"],
        ["Cynical commercial developers", "Lack of social conscience"],
        "Designs free public nature playgrounds and restorative parks in high-density urban areas.",
        ["Share my passion for creating green healing spaces for urban youth."],
        archetype_id="grounded_sanctuary", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Transforming industrial wastelands into vibrant municipal parks for children.")
    pairs.append(ConversationalBenchmarkPair("community_health_allies", p29a, p29b,
        "Pediatric clinic director meets public playground architect",
        "Deep shared devotion to urban child welfare, community healing, and civic spaces",
        9.3, "Pediatric care and child play architecture aligned into profound shared life purpose.",
        "true_positive", 6.7))

    # 30. eco_architect_sanctuary
    p30a = _build_research_persona("study-30a", "Maya Lund", "Sustainable Mass Timber Architect",
        ["Timber Architecture", "Permaculture", "Trail Running"], ["Cross-laminated timber", "Passive house", "Mornings"], "Regenerative design",
        ["A partner who loves land stewardship, timber building, and regenerative homesteading"],
        ["High-consumption suburban lifestyle", "Indifference to ecological footprint"],
        "Designs zero-carbon passive timber buildings; plans to build a collaborative eco-homestead.",
        ["Ask if they dream of building a zero-carbon regenerative homestead."],
        archetype_id="visionary_builder", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Co-designing a net-zero regenerative eco-village built from sustainable mass timber.")
    p30b = _build_research_persona("study-30b", "Noah Green", "Permaculture Agroforestry Steward",
        ["Permaculture", "Timber Architecture", "Plant Propagation"], ["Food forests", "Soil biology", "Timber framing"], "Regenerative design",
        ["A visionary partner to co-create a regenerative agroforestry farm and timber dwelling"],
        ["Conventional industrial farming", "Chemical landscaping"],
        "Restoring 80 acres of degraded agricultural land into perennial food forests.",
        ["Discuss food forests and building timber passive houses."],
        archetype_id="grounded_sanctuary", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Restoring 80-acre resilient food forest and building sustainable timber home.")
    pairs.append(ConversationalBenchmarkPair("eco_architect_sanctuary", p30a, p30b,
        "Sustainable timber architect meets permaculture agroforestry steward",
        "Regenerative land stewardship meets carbon-negative passive timber design",
        9.4, "Visionary architecture and ecological agriculture clicked into an extraordinary joint dream.",
        "true_positive", 6.9))

    # 31. mindful_triathlon_partners
    p31a = _build_research_persona("study-31a", "Liam Patel", "Biomedical Systems Researcher & Triathlete",
        ["Triathlon", "Specialty Coffee", "Plant-Based Nutrition"], ["Endurance physiology", "Mornings", "Grounded science"], "Dawn endurance discipline",
        ["A partner who loves early dawn athletic training and conscious emotional health"],
        ["Heavy drinking", "Smoking", "Chaotic late-night habits"],
        "Wakes at 5:15 AM for dawn endurance training; emotionally secure, values daily calm consistency.",
        ["Ask what time they naturally wake up and how they view dawn exercise."],
        archetype_id="holistic_seeker", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Qualifying for Ironman world championship while directing cardiovascular research.")
    p31b = _build_research_persona("study-31b", "Zoe Campbell", "Sports Nutritionist & Trail Marathoner",
        ["Triathlon", "Specialty Coffee", "Plant-Based Nutrition"], ["Metabolic health", "Trail ultra", "Pour-over"], "Dawn endurance discipline",
        ["An early-rising endurance partner with clean nutritional habits and grounded warmth"],
        ["Sedentary lifestyle", "Toxic hustle culture without recovery"],
        "Runs trail marathons at sunrise; values somatic recovery, clean fuel, and deep mutual respect.",
        ["Share my love for 5:30 AM dawn trail runs and nutritional recovery."],
        archetype_id="holistic_seeker", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Authoring foundational guide on plant-based athletic longevity and endurance recovery.")
    pairs.append(ConversationalBenchmarkPair("mindful_triathlon_partners", p31a, p31b,
        "Biomedical researcher & sports nutritionist (both triathletes)",
        "Dawn athletic discipline, metabolic longevity, clean nutrition, and secure emotional grounding",
        9.0, "Dawn schedules, endurance philosophies, and mutual emotional calm established deep bond.",
        "true_positive", 7.3))

    # 32. literary_translators_dialogue
    p32a = _build_research_persona("study-32a", "Soraya Fassi", "Persian Poetry Translator & Essayist",
        ["Literary Translation", "Book Collecting", "Calligraphy"], ["Sufi poetry", "Comparative literature", "Black tea"], "Reflective intellectual",
        ["A scholarly partner who loves rare books, linguistic nuance, and quiet libraries"],
        ["Anti-intellectualism", "Impatient modern slang obsessed partners"],
        "Translates 12th-century Persian mystics; cherishes contemplative evenings among books.",
        ["Ask about their favourite untranslatable words and appreciation for poetry."],
        archetype_id="contemplative_craftsman", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Translating complete works of medieval Persian mystic poets for university press.")
    p32b = _build_research_persona("study-32b", "Julian Mercier", "Comparative Philologist & Latin Scholar",
        ["Literary Translation", "Book Collecting", "Classical Guitar"], ["Etymology", "Historical linguistics", "Tea"], "Reflective intellectual",
        ["A multilingual partner who cherishes ancient texts, poetry, and contemplative dialogue"],
        ["Shallow superficial conversation", "Disdain for history"],
        "Researches linguistic evolution across Mediterranean texts; seeks life partner for quiet scholarship.",
        ["Mention my obsession with untranslatable idioms and classical etymology."],
        archetype_id="intellectual_synthesizer", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Publishing historical etymological dictionary while building personal scholarly library.")
    pairs.append(ConversationalBenchmarkPair("literary_translators_dialogue", p32a, p32b,
        "Persian literature translator meets comparative philologist",
        "Profound literary translation, shared comparative philology passion, and quiet library life",
        9.2, "Dialogue on untranslatable poetic meter and etymology revealed rare intellectual soulmates.",
        "true_positive", 7.1))

    # =========================================================================
    # CATEGORY 5: Work/Life Boundaries & Ambition Tempo Friction
    # =========================================================================
    # 33. ambition_tempo_friction
    p33a = _build_research_persona("study-33a", "Sameer Bajaj", "Early-Stage VC Partner",
        ["Angel Investing", "Podcasts", "Golf"], ["Venture growth", "Cocktail mixers", "Fintech"], "Hyper-growth networking",
        ["A partner willing to attend 4 evening tech networking galas a week"],
        ["People who want to stay home on Friday nights", "Slow career momentum"],
        "Attends 4 evening networking mixers weekly; career is all-consuming social performance.",
        ["Ask if they enjoy high-profile tech networking dinners."],
        archetype_id="high_velocity_strategist", attachment_style="Secure", conflict_style="Direct candor",
        future_horizon="Raising $150M early-stage venture fund and expanding global LP network.")
    p33b = _build_research_persona("study-33b", "Anita Sengupta", "Local Public Library Archivist",
        ["Archival Preservation", "Bookbinding", "Botanical Walks"], ["Local history", "Herbal tea", "Quiet evenings"], "Offline peaceful sanctuary",
        ["A peaceful homebody partner who cherishes quiet offline evenings"],
        ["Superficial networking climbers", "Loud corporate galas"],
        "Protects local history manuscripts; requires quiet offline evenings to recharge.",
        ["Be clear that I value peaceful quiet evenings and dislike corporate networking."],
        archetype_id="contemplative_craftsman", attachment_style="Secure", conflict_style="Gentle de-escalation",
        future_horizon="Leading municipal historical archive preservation in quiet civic library.")
    pairs.append(ConversationalBenchmarkPair("ambition_tempo_friction", p33a, p33b,
        "Early-stage VC partner vs public library archivist",
        "4-night/week tech networking galas vs quiet offline homebody sanctuary",
        4.0, "Sameer named high-velocity networking calendar; Anita confirmed need for quiet evenings. Friction.",
        "tempo_friction", 7.1))

    # 34. social_battery_clash
    p34a = _build_research_persona("study-34a", "Varun Nair", "Electronic Festival Producer",
        ["Music Festivals", "DJing", "Nightlife"], ["Stage production", "Electronic music", "Club mixers"], "Late-night high octane",
        ["A partner who loves dancing till 4 AM at warehouse parties and weekend festivals"],
        ["Homebodies who get tired at 10 PM"],
        "Produces major electronic music festivals; weekends are 72-hour non-stop loud crowds.",
        ["Check if they love attending late-night music festivals and warehouse events."],
        archetype_id="high_octane_catalyst", attachment_style="Secure", conflict_style="Direct candor",
        future_horizon="Producing international electronic music festivals across Europe and Latin America.")
    p34b = _build_research_persona("study-34b", "Leela Krishnan", "Rare Manuscript Conservator",
        ["Museum Exhibitions", "Calligraphy", "Tea Ceremonies"], ["Paper chemistry", "Meditation", "Solitude"], "Low-stimulation tranquility",
        ["A gentle partner who loves low-stimulation quiet environments"],
        ["Loud nightclubs", "Warehouse raves", "Chaotic loud environments"],
        "Sensory sensitive; social battery depletes after 60 minutes in noisy crowds.",
        ["Be upfront that loud clubs and raves drain my nervous system completely."],
        archetype_id="contemplative_craftsman", attachment_style="Secure", conflict_style="Gentle de-escalation",
        future_horizon="Restoring medieval Japanese woodblock manuscripts in quiet conservation lab.")
    pairs.append(ConversationalBenchmarkPair("social_battery_clash", p34a, p34b,
        "Festival producer vs rare manuscript conservator",
        "4 AM warehouse parties vs low-stimulation sensory sanctuary",
        3.8, "Varun described 72-hour festival schedules. Leela named 60-minute sensory limit; battery mismatch.",
        "tempo_friction", 7.2))

    # 35. corporate_rat_race_vs_homestead
    p35a = _build_research_persona("study-35a", "Damon Scott", "Managing Director in Leveraged Finance",
        ["Fine Dining", "Golf", "Private Equity"], ["Capital markets", "Luxury watches", "High status"], "Executive corporate hustle",
        ["A polished metropolitan partner who values executive status and Manhattan lifestyle"],
        ["Off-grid hippies", "Anti-capitalist stances", "Living in rural dirt"],
        "Works 75 hours a week in finance; proud of executive status and luxury high-rise life.",
        ["Ask if they appreciate metropolitan ambition and executive lifestyle."],
        archetype_id="high_velocity_strategist", attachment_style="Secure", conflict_style="Direct candor",
        future_horizon="Managing $2B private debt fund while living in luxury Manhattan penthouse.")
    p35b = _build_research_persona("study-35b", "Willow Hayes", "Off-Grid Goat Farmer & Cheesemaker",
        ["Goat Farming", "Fermentation", "Solar Energy"], ["Raw milk cheese", "Compost", "Homesteading"], "Earth-rooted off-grid",
        ["A simple, grounded partner who respects manual labor and loves living off-grid"],
        ["Corporate finance suits", "Materialistic status symbol obsession"],
        "Lives in solar-powered yurts; makes artisanal goat cheese and abhors corporate finance greed.",
        ["Ask what they think of leaving cities to work with dirt and animals."],
        archetype_id="grounded_sanctuary", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Expanding off-grid artisanal goat dairy farm and teaching homesteading skills.")
    pairs.append(ConversationalBenchmarkPair("corporate_rat_race_vs_homestead", p35a, p35b,
        "Manhattan finance VP vs off-grid goat cheese farmer",
        "Luxury high-rise executive ambition vs off-grid yurt homesteading and dirt",
        3.5, "Damon spoke of private equity status; Willow shared off-grid yurt life. Mutual value mismatch.",
        "tempo_friction", 5.9))

    # 36. hustle_culture_vs_sabbatical
    p36a = _build_research_persona("study-36a", "Evan Ross", "SaaS Growth Hacker & Serial Founder",
        ["Growth Hacking", "Keto", "Cryptocurrency"], ["Cold outreach", "Conversion funnels", "Hustle"], "24/7 grind mindset",
        ["An equally relentless partner who optimizes every hour for financial upside"],
        ["People who take gap years or work non-profits", "Unambitious slackers"],
        "Believes rest is for the weak; tracks daily productivity in 15-minute timeblocks.",
        ["Ask if they have an obsessive drive to build 8-figure wealth."],
        archetype_id="visionary_builder", attachment_style="Dismissive-Avoidant", conflict_style="Direct candor",
        future_horizon="Building and flipping multiple SaaS ventures for 8-figure exits.")
    p36b = _build_research_persona("study-36b", "Maya Sundaram", "Meditation Resident & Hospice Caregiver",
        ["Vipassana", "Death Doula Work", "Slow Walking"], ["End-of-life care", "Presence", "Meditation"], "Spiritual surrender",
        ["A compassionate partner who values presence, non-attachment, and emotional depth"],
        ["Obsession with money", "Frantic hustle bro culture", "Disdain for mortality"],
        "Spends 6 months a year in silent meditation and caring for dying patients in hospice.",
        ["Share how caring for the dying teaches the vanity of chasing money."],
        archetype_id="holistic_seeker", attachment_style="Secure", conflict_style="Gentle de-escalation",
        future_horizon="Founding compassionate contemplative hospice sanctuaries for dignified end-of-life care.")
    pairs.append(ConversationalBenchmarkPair("hustle_culture_vs_sabbatical", p36a, p36b,
        "Growth hacker hustle bro vs hospice meditation caregiver",
        "15-minute optimization for wealth vs contemplative presence and end-of-life hospice care",
        3.6, "Evan pitched 8-figure grind. Maya spoke of presence and mortality; irreconcilable worldviews.",
        "tempo_friction", 6.3))

    # 37. two_alpha_builders_clash
    p37a = _build_research_persona("study-37a", "Ron Chen", "Series B AI Foundation Model CEO",
        ["Artificial Intelligence", "Venture Capital", "Marathon"], ["Neural scaling", "Founding", "Compute clusters"], "Commanding founder",
        ["A supportive partner who will relocate to San Francisco and support my startup as priority #1"],
        ["Partners who refuse to move to SF", "Someone who demands equal priority for their company"],
        "San Francisco AI founder; expects partner to relocate to SF and adapt to his 80-hour founder schedule.",
        ["Confirm they are willing to base life in San Francisco around my company."],
        archetype_id="visionary_builder", attachment_style="Dismissive-Avoidant", conflict_style="Direct candor",
        future_horizon="Building multi-billion dollar frontier AI lab headquartered in San Francisco.")
    p37b = _build_research_persona("study-37b", "Alex Mercer", "Series B Robotics Hardware CEO",
        ["Robotics", "Venture Capital", "CrossFit"], ["Hardware fab", "Factory automation", "Leading"], "Commanding founder",
        ["A supportive partner who will relocate to Boston and prioritize my robotics factories"],
        ["Partners who refuse to move to Boston", "Someone who expects me to subordinate my mission"],
        "Boston robotics founder; non-negotiable headquarters in Massachusetts; will never relocate to SF.",
        ["Make sure they understand my robotics manufacturing must remain in Boston."],
        archetype_id="visionary_builder", attachment_style="Dismissive-Avoidant", conflict_style="Direct candor",
        future_horizon="Scaling advanced humanoid robotics manufacturing plants across Boston.")
    pairs.append(ConversationalBenchmarkPair("two_alpha_builders_clash", p37a, p37b,
        "Both Series B venture-backed tech CEOs ('AI & Robotics')",
        "Two uncompromising founders: Ron demands SF base; Alex demands Boston factory base",
        3.8, "Both CEOs demanded the other relocate headquarters. Neither willing to compromise; deadlock.",
        "tempo_friction", 8.8))

    # 38. frugal_homesteader_vs_jetsetter
    p38a = _build_research_persona("study-38a", "Silas Finch", "Zero-Waste Tool Repairman",
        ["Tool Restoration", "Thrifting", "Bicycle Commuting"], ["Circular economy", "Repair culture", "Frugality"], "Extreme frugal repair",
        ["A partner committed to zero-waste, thrifting, and never spending on luxury goods"],
        ["Designer clothes", "Luxury consumerism", "Uber rides"],
        "Spends $200 a month total; repairs old bicycles and refuses to buy anything new.",
        ["Ask if they believe in repairing everything rather than buying new things."],
        archetype_id="intentional_minimalist", attachment_style="Secure", conflict_style="Direct candor",
        future_horizon="Establishing a community tool library and zero-waste cooperative repair guild.")
    p38b = _build_research_persona("study-38b", "Genevieve De La Tour", "High-Fashion PR Director",
        ["Haute Couture", "Champagne", "First-Class Travel"], ["Fashion week", "Designer aesthetics", "Luxury PR"], "High-end luxury glamour",
        ["An elegant, affluent partner who loves Milan fashion weeks and 5-star travel"],
        ["Thrift stores", "Cheapness", "Shabby appearance"],
        "Lives in designer couture; attends fashion galas in Milan and Paris; views thrifting as depressing.",
        ["Mention my favourite couture shows in Paris and luxury weekend getaways."],
        archetype_id="sensual_epicurean", attachment_style="Secure", conflict_style="Direct candor",
        future_horizon="Directing international luxury fashion PR campaigns across Paris, Milan, and New York.")
    pairs.append(ConversationalBenchmarkPair("frugal_homesteader_vs_jetsetter", p38a, p38b,
        "Zero-waste tool repairman vs luxury fashion PR director",
        "$200/month bicycle repair minimalism vs Paris couture fashion weeks and champagne",
        3.2, "Silas condemned consumerism; Genevieve stated luxury lifestyle necessity. Financial gulf.",
        "tempo_friction", 6.1))

    # 39. perpetual_student_vs_pragmatic_builder
    p39a = _build_research_persona("study-39a", "Hugo Becker", "12th-Year PhD Philosophy Candidate",
        ["Phenomenology", "Coffee", "Chess"], ["Heidegger", "Academic debate", "Reading"], "Unending scholarly delay",
        ["A patient partner willing to support my unending intellectual dissertation"],
        ["People who ask when I will get a real job", "Commercial corporate mindsets"],
        "Has been writing the same dissertation for 12 years with zero income or timeline to finish.",
        ["Ask if they value pure philosophy above practical financial security."],
        archetype_id="intellectual_synthesizer", attachment_style="Fearful-Avoidant", conflict_style="Collaborative problem-solver",
        future_horizon="Finishing theoretical dissertation on post-Kantian phenomenology eventually.")
    p39b = _build_research_persona("study-39b", "Nadia Al-Amin", "Municipal Infrastructure Project Director",
        ["Civil Engineering", "Project Management", "Rowing"], ["Bridge construction", "Public transit", "Budgeting"], "Concrete delivery rigor",
        ["A decisive partner who executes projects, earns a living, and values real-world results"],
        ["Perpetual students with no execution", "Financial unreliability"],
        "Manages $400M bridge construction budgets; zero patience for academic procrastination without results.",
        ["Ask what tangible real-world projects they have completed in the last 3 years."],
        archetype_id="high_velocity_strategist", attachment_style="Secure", conflict_style="Direct candor",
        future_horizon="Directing billion-dollar high-speed regional rail infrastructure programs.")
    pairs.append(ConversationalBenchmarkPair("perpetual_student_vs_pragmatic_builder", p39a, p39b,
        "12th-year philosophy student vs civil engineering infrastructure director",
        "Endless theoretical dissertation delay vs $400M bridge execution and financial accountability",
        4.2, "Nadia probed career execution timelines; Hugo defended endless dissertation. Practical friction.",
        "tempo_friction", 6.5))

    # 40. night_shift_er_vs_9to5_routine
    p40a = _build_research_persona("study-40a", "Dr. Sean O'Connor", "Nocturnist Trauma Physician",
        ["Emergency Medicine", "Dark Rooms", "Mountain Biking"], ["Trauma resuscitation", "Circadian biology", "Blackout curtains"], "Inverted nocturnal",
        ["A partner who understands and adapts to an inverted 7 PM to 7 AM sleep schedule"],
        ["Demands for early breakfast dates", "People who cannot sleep during the day"],
        "Works 7 PM to 7 AM night shifts year-round; sleeps 9 AM to 5 PM behind blackout curtains.",
        ["Explain that my entire life runs on nocturnal night-shift hours."],
        archetype_id="resilient_pillar", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Directing nocturnal emergency trauma center while optimizing shift-worker longevity.")
    p40b = _build_research_persona("study-40b", "Grace Sterling", "Montessori Kindergarten Headmistress",
        ["Early Childhood Education", "Morning Gardening", "Baking"], ["Child development", "Dawn walks", "Morning tea"], "Early morning diurnal",
        ["A diurnal partner who wakes at 6 AM and loves cheerful daytime weekend routines"],
        ["Night owls who sleep all day", "Partners unavailable during daylight weekends"],
        "Starts school at 7:30 AM every morning; asleep by 9:30 PM; lives for bright morning sun.",
        ["Ask if they love early morning sunshine and daytime weekend adventures."],
        archetype_id="grounded_sanctuary", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Expanding nature-based early childhood education sanctuaries across regional towns.")
    pairs.append(ConversationalBenchmarkPair("night_shift_er_vs_9to5_routine", p40a, p40b,
        "Nocturnist ER doctor vs Montessori kindergarten headmistress",
        "7 PM to 7 AM nocturnal hospital shift vs 6 AM dawn kindergarten routine (inverted lives)",
        4.4, "Sean and Grace mapped their daily clocks: completely opposite circadian existence.",
        "tempo_friction", 6.6))

    # =========================================================================
    # CATEGORY 6: Moderate / Lukewarm Rapport & Platonic Friend Zone
    # =========================================================================
    # 41. polite_zero_spark
    p41a = _build_research_persona("study-41a", "Aditya Verma", "Cloud Operations Specialist",
        ["Running", "Podcasts", "Board Games"], ["DevOps", "Tech blogs", "Coffee"], "Steady corporate",
        ["A pleasant partner to share comfortable routines with"], ["Drama", "Unpredictability"],
        "Polite, quiet professional; rarely initiates banter or vulnerable self-disclosure.",
        ["Keep the conversation pleasant and professional."],
        archetype_id="resilient_pillar", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Advancing in enterprise cloud operations while maintaining comfortable domestic routines.")
    p41b = _build_research_persona("study-41b", "Neha Kapoor", "Corporate Compliance Manager",
        ["Running", "Podcasts", "Cooking"], ["Regulatory audits", "Food prep", "Reading"], "Steady corporate",
        ["A reliable partner who respects schedules and polite communication"], ["Reckless people", "Poor manners"],
        "Courteous and structured; treats dates like friendly performance appraisals.",
        ["Be courteous and check their lifestyle stability."],
        archetype_id="resilient_pillar", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Leading corporate regulatory compliance programs in multinational enterprise.")
    pairs.append(ConversationalBenchmarkPair("polite_zero_spark", p41a, p41b,
        "Both list 'Running' and 'Podcasts' (safe corporate overlap)",
        "Both polite and stable, but zero chemistry, flirting, or emotional vulnerability",
        4.8, "Conversation was pleasant, structured, and thoroughly unromantic. Mutual polite pass.",
        "lukewarm", 6.7))

    # 42. mismatched_tempo
    p42a = _build_research_persona("study-42a", "Rohan Mehra", "Fast-Talking Auctioneer & Broker",
        ["Public Speaking", "Basketball", "Podcasts"], ["Auctions", "Real estate", "Fast cars"], "Rapid-fire extrovert",
        ["A fast-witted partner who speaks at lightning speed and keeps up with rapid chatter"], ["Slow talkers", "Long awkward pauses"],
        "Speaks 200 words a minute; gets visibly impatient during silences or pauses.",
        ["Keep the energy high and fast-paced."],
        archetype_id="high_velocity_strategist", attachment_style="Secure", conflict_style="Direct candor",
        future_horizon="Expanding commercial real estate auction syndicates across major metropolitan markets.")
    p42b = _build_research_persona("study-42b", "Maya Soni", "Zen Calligrapher & Essayist",
        ["Japanese Tea", "Calligraphy", "Meditation"], ["Inks", "Zen aesthetics", "Silence"], "Slow contemplative pauses",
        ["A partner who allows 10-second pauses before speaking and values spacious silence"],
        ["Fast talkers who interrupt or cannot sit in silence"],
        "Takes 10-second contemplative pauses before answering; feels overwhelmed by fast chatter.",
        ["Take time before speaking; let silence breathe between words."],
        archetype_id="contemplative_craftsman", attachment_style="Secure", conflict_style="Gentle de-escalation",
        future_horizon="Publishing monographs on meditative Japanese calligraphy in quiet mountain studio.")
    pairs.append(ConversationalBenchmarkPair("mismatched_tempo", p42a, p42b,
        "High-energy auctioneer vs meditative Zen calligrapher",
        "Rohan rapid-fire speech vs Maya 10-second introspective pauses: acoustic mismatch",
        4.6, "Rohan repeatedly spoke over Maya pauses; Maya felt overwhelmed by machine-gun tempo.",
        "lukewarm", 6.4))

    # 43. humor_disconnect
    p43a = _build_research_persona("study-43a", "Kunal Batra", "Satirical Novelist & Dark Comic",
        ["Satire", "Cinema", "Dark Chocolate"], ["Irony", "Absurdism", "Dry humor"], "Dry intellectual deadpan",
        ["A partner who loves biting deadpan satire, absurdity, and dark intellectual jokes"], ["Earnest literalists who take everything personally"],
        "Speaks almost entirely in deadpan irony and satire; rarely drops the comedic mask.",
        ["Use dry deadpan satire to see if they understand my sense of humor."],
        archetype_id="playful_maverick", attachment_style="Secure", conflict_style="Direct candor",
        future_horizon="Publishing acclaimed series of satirical fiction exploring modern absurdities.")
    p43b = _build_research_persona("study-43b", "Ananya Joshi", "Primary School Counselor",
        ["Children's Theater", "Gardening", "Tea"], ["Warmth", "Child psychology", "Empathy"], "Warm earnest sincerity",
        ["A warm, straightforward, earnest partner who says what they mean without sarcasm"], ["Sarcasm", "Cynicism", "Deadpan irony"],
        "Deeply literal and sincere; feels confused and wounded by irony, mockery, or deadpan sarcasm.",
        ["Be warm and earnest; make sure they are kind and mean what they say."],
        archetype_id="empathic_healer", attachment_style="Secure", conflict_style="Gentle de-escalation",
        future_horizon="Developing emotional literacy curriculums for elementary schools.")
    pairs.append(ConversationalBenchmarkPair("humor_disconnect", p43a, p43b,
        "Satirical novelist vs earnest school counselor",
        "Kunal dry deadpan satire vs Ananya warm literal earnestness: humor disconnect",
        4.7, "Kunal jokes landed with confusion; Ananya found irony cynical. Harmless but disconnected.",
        "lukewarm", 6.6))

    # 44. platonic_friend_zone
    p44a = _build_research_persona("study-44a", "Dev Roy", "Sports Documentary Cameraman",
        ["Bouldering", "Photography", "Breweries"], ["Sports action", "Documentary", "Camping"], "Easygoing buddy",
        ["A fun, adventurous companion for climbing and road trips"], ["High romantic drama"],
        "Warm, funny, completely platonic energy; gives off 'cool bro' vibes with zero romantic tension.",
        ["Keep it friendly and relaxed; talk about sports and trips."],
        archetype_id="playful_maverick", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Documenting extreme alpine bouldering expeditions around the world.")
    p44b = _build_research_persona("study-44b", "Ritu Sharma", "Event Coordinator & Hiker",
        ["Bouldering", "Photography", "Travel"], ["Events", "Outdoor hikes", "Music"], "Energetic peer",
        ["A romantic spark with real masculine mystery and emotional depth"], ["Guys who feel like college buddies"],
        "Looking for romantic passion and depth; easily slots sporty peers into the friend-zone.",
        ["See if there is real romantic intrigue, not just 'one of the guys' energy."],
        archetype_id="high_octane_catalyst", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Managing world-class experiential marketing festivals across international venues.")
    pairs.append(ConversationalBenchmarkPair("platonic_friend_zone", p44a, p44b,
        "Both list 'Bouldering' and 'Photography'",
        "Great mutual banter about cameras and climbing, but 100% platonic buddy energy",
        4.9, "Excellent conversation about climbing routes, but zero romantic spark. Friend-zone confirmed.",
        "lukewarm", 7.0))

    # 45. polite_dinner_interview
    p45a = _build_research_persona("study-45a", "Karthik Ram", "Supply Chain Logistics VP",
        ["Chess", "Golf", "Economic History"], ["Supply chains", "Process optimization", "Espresso"], "Structured formal",
        ["A competent, poised partner with impeccable professional pedigree"], ["Disorganized flaky people"],
        "Extremely formal manners; conducts dates with structured questions resembling quarterly business reviews.",
        ["Maintain structured questions to assess mutual capability and alignment."],
        archetype_id="high_velocity_strategist", attachment_style="Secure", conflict_style="Direct candor",
        future_horizon="Optimizing global maritime logistics networks for international shipping conglomerate.")
    p45b = _build_research_persona("study-45b", "Shalini Saxena", "Corporate Tax Director",
        ["Chess", "Tennis", "Classical Piano"], ["Tax treaties", "Audits", "Fine tea"], "Formal structured",
        ["A dignified partner who conducts themselves with decorum and respect"], ["Informal slang", "Messy people"],
        "Very poised and formal; answered questions like a board member at a stakeholder meeting.",
        ["Be poised, professional, and observe their composure under questioning."],
        archetype_id="high_velocity_strategist", attachment_style="Secure", conflict_style="Direct candor",
        future_horizon="Advising sovereign wealth funds on international cross-border tax treaties.")
    pairs.append(ConversationalBenchmarkPair("polite_dinner_interview", p45a, p45b,
        "Both list 'Chess' and high corporate finance tags",
        "Both highly competent, but date felt like a formal corporate board interview",
        4.5, "Exchanged impressive credentials politely; neither felt romantic warmth. Respectful pass.",
        "lukewarm", 6.8))

    # 46. parallel_strangers
    p46a = _build_research_persona("study-46a", "Vivek Nambiar", "Database Kernel Architect",
        ["Linux", "Sci-Fi", "Espresso"], ["B-trees", "Storage engines", "History"], "Quiet introverted",
        ["A quiet, low-maintenance partner who is content sharing space without pressure"], ["Demanding socialites"],
        "Very quiet; polite nodding, but rarely asks follow-up questions about the other person.",
        ["Be polite and share my thoughts if asked."],
        archetype_id="contemplative_craftsman", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Authoring open-source distributed database engine adopted by thousands of engineers.")
    p46b = _build_research_persona("study-46b", "Meagan Ross", "Data Governance Analyst",
        ["Sci-Fi", "Baking", "Tea"], ["Information architecture", "Bread", "Reading"], "Quiet introverted",
        ["A conversational partner who takes initiative and shows active curiosity about my mind"], ["Silent withdrawn men"],
        "Reserved and introspective; needs the other person to actively draw her out with questions.",
        ["Wait to see if they take the lead and ask curious questions."],
        archetype_id="cozy_domesticist", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Designing ethical information governance standards for national health databases.")
    pairs.append(ConversationalBenchmarkPair("parallel_strangers", p46a, p46b,
        "Both list 'Sci-Fi' and technical roles",
        "Both reserved; Vivek waited for questions, Meagan waited for initiative; conversation stalled",
        4.7, "Neither initiated proactive curiosity; polite nodding in parallel without connection.",
        "lukewarm", 6.3))

    # 47. warm_cousin_energy
    p47a = _build_research_persona("study-47a", "Toby Miller", "Youth Community Soccer Coach",
        ["Soccer", "Camping", "Board Games"], ["Coaching", "Outdoor games", "BBQ"], "Wholesome upbeat",
        ["A warm, cheerful partner to enjoy family BBQs and outdoor games with"], ["Pessimistic cynics"],
        "Golden retriever energy; cheerful, wholesome, treats dates with friendly sibling warmth.",
        ["Be upbeat, positive, and talk about camping and games."],
        archetype_id="grounded_sanctuary", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Running regional non-profit sports camps for underprivileged youth.")
    p47b = _build_research_persona("study-47b", "Sarah Jenkins", "Middle School Science Teacher",
        ["Camping", "Nature Crafts", "Board Games"], ["Teaching", "Science fairs", "Baking"], "Wholesome nurturing",
        ["An engaging partner with romantic mystery and flirtatious chemistry"], ["Feeling like family relatives"],
        "Warm and friendly; noted that Toby felt exactly like her wholesome favorite cousin.",
        ["See if there is flirtatious romantic chemistry, not just wholesome buddy vibe."],
        archetype_id="grounded_sanctuary", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Developing experiential nature science curricula for middle school students.")
    pairs.append(ConversationalBenchmarkPair("warm_cousin_energy", p47a, p47b,
        "Both list 'Camping' and 'Board Games'",
        "Warm, wholesome, zero conflict, but felt 100% like brother-sister cousin energy",
        5.0, "Great mutual warmth and wholesome laughter; zero flirtatious attraction or romantic spark.",
        "lukewarm", 6.9))

    # 48. agreeable_apathy
    p48a = _build_research_persona("study-48a", "Ethan Shaw", "Land Surveyor & Cartographer",
        ["Hiking", "Coffee", "Documentaries"], ["Topography", "Old maps", "Walks"], "Even-keeled agreeable",
        ["Anyone kind and easygoing who doesn't cause stress"], ["Extreme conflict or strong demands"],
        "Agrees with whatever the other person says; has no strong personal opinions or passions.",
        ["Just agree with their preferences and keep things smooth."],
        archetype_id="resilient_pillar", attachment_style="Secure", conflict_style="Gentle de-escalation",
        future_horizon="Surveying regional wilderness boundary lands with quiet topographic instruments.")
    p48b = _build_research_persona("study-48b", "Clara Higgins", "GIS Mapping Specialist",
        ["Hiking", "Coffee", "Documentaries"], ["Geospatial analysis", "Satellite data", "Reading"], "Even-keeled agreeable",
        ["A partner with bold passions, strong convictions, and distinct opinions"], ["People who have no opinions of their own"],
        "Polite and easygoing, but seeks partner with strong passionate convictions and distinct voice.",
        ["See if they have strong convictions and things they truly fight for."],
        archetype_id="contemplative_craftsman", attachment_style="Secure", conflict_style="Collaborative problem-solver",
        future_horizon="Building open-source satellite climate mapping tools for environmental NGOs.")
    pairs.append(ConversationalBenchmarkPair("agreeable_apathy", p48a, p48b,
        "Both list 'Hiking', 'Coffee', and 'Documentaries'",
        "Ethan agreed with everything; Clara felt complete absence of passion or conviction",
        4.8, "Conversation was completely frictionless and completely unmemorable. Agreeable apathy.",
        "lukewarm", 6.5))

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
    internal_cons_scores = []

    for idx, pair in enumerate(cohort, 1):
        pa, pb = pair.person_a, pair.person_b
        store.save_person(pa)
        store.save_person(pb)
        
        # 1. Baseline: Profile-Only Prior Score (y_prior)
        c = compat.compute(pa.analysis, pb.analysis)
        y_prior = round(float(c.prior), 2)
        
        # 2. Treatment: Conversational Date Real Agent Verdict Score (y_agent)
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
        y_cons = pair.internal_consistency_score

        err_prior = abs(y_prior - y_gt)
        err_agent = abs(y_agent - y_gt)

        prior_errors.append(err_prior)
        agent_errors.append(err_agent)
        
        gt_scores.append(y_gt)
        prior_scores.append(y_prior)
        agent_scores.append(y_agent)
        internal_cons_scores.append(y_cons)

        print(f"[{idx:02d}/{len(cohort)}] {pair.pair_id:32s}: Prior={y_prior:4.1f}, Agent={y_agent:4.1f}, GT={y_gt:4.1f} (engine={d_rec.engine})", flush=True)

        pair_results.append({
            "pair_id": pair.pair_id,
            "category": pair.category,
            "name_a": pa.analysis.display_name,
            "name_b": pb.analysis.display_name,
            "public_overlap_summary": pair.public_overlap_summary,
            "hidden_conversational_facts": pair.hidden_conversational_facts,
            "discovery_narrative": pair.discovery_narrative,
            "ground_truth_score": y_gt,
            "baseline_prior_score": y_prior,
            "agent_verdict_score": y_agent,
            "internal_consistency_score": y_cons,
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
    internal_cons_rho = spearman_rho(internal_cons_scores, gt_scores)
    agent_vs_internal_rho = spearman_rho(agent_scores, internal_cons_scores)

    # Specific category detection metrics
    attach_traps = [p for p in pair_results if p["category"] == "attachment_trap"]
    attach_detected = sum(1 for p in attach_traps if p["agent_verdict_score"] <= 3.5)
    attach_detection_rate = round(attach_detected / max(1, len(attach_traps)) * 100, 1)

    comp_gems = [p for p in pair_results if p["category"] == "complementary_gem"]
    comp_recovered = sum(1 for p in comp_gems if p["agent_verdict_score"] >= 8.0)
    comp_recovery_rate = round(comp_recovered / max(1, len(comp_gems)) * 100, 1)

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
            "internal_consistency_rho": internal_cons_rho,
            "agent_vs_internal_consistency_rho": agent_vs_internal_rho,
            "attachment_trap_detection_rate_pct": attach_detection_rate,
            "complementary_synergy_recovery_rate_pct": comp_recovery_rate,
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
    cons_rho = float(metrics.get("internal_consistency_rho", 0.0))

    engine_name = study.get("engine") or metrics.get("engine") or "offline_deterministic"
    is_llm = bool(study.get("llm_enabled") or metrics.get("llm_enabled", False))
    engine_badge_text = f"ENGINE: {engine_name.upper()} (LIVE LLM)" if is_llm else "ENGINE: OFFLINE DETERMINISTIC (HEURISTIC BASELINE)"
    engine_bg = "rgba(46,160,67,0.18)" if is_llm else "rgba(210,153,34,0.18)"
    engine_stroke = "#2ea043" if is_llm else "#d29922"
    engine_color = "#3fb950" if is_llm else "#ffb703"
    badge_width = max(190, len(engine_badge_text) * 7 + 22)

    n = len(pairs)
    chart_w = max(1360, n * 29 + 120)
    chart_h = 600
    margin_left, margin_top = 70, 150
    bar_area_w = chart_w - margin_left - 50
    bar_area_h = 290
    group_w = bar_area_w / max(1, n)
    bar_w = min(12, max(6, group_w * 0.38))
    val_font_size = 8 if n > 24 else 10
    label_font_size = 8 if n > 24 else 11

    # Highlight Gain Pill 1 (Top Right): Error Reduction
    pill1_w = 330
    pill1_x = chart_w - pill1_w - 30
    gain_pill1_svg = f"""
    <g transform="translate({pill1_x}, 32)">
      <rect width="{pill1_w}" height="54" rx="10" fill="rgba(46,160,67,0.15)" stroke="#2ea043" stroke-width="1.5"/>
      <text x="{pill1_w / 2}" y="22" fill="#3fb950" font-family="-apple-system, sans-serif" font-size="12" font-weight="800" text-anchor="middle">
        {pct_reduction}% CALIBRATION ERROR REDUCTION
      </text>
      <text x="{pill1_w / 2}" y="42" fill="#8b949e" font-family="-apple-system, sans-serif" font-size="11" text-anchor="middle">
        Ranking &rho;: {rho_prior:+.2f} &rarr; {rho_agent:+.2f} ({rho_agent - rho_prior:+.2f} gain)
      </text>
    </g>
    """

    # Highlight Pill 2 (Internal Consistency vs Real Compatibility)
    pill2_w = 340
    pill2_x = pill1_x - pill2_w - 14
    gain_pill2_svg = f"""
    <g transform="translate({pill2_x}, 32)">
      <rect width="{pill2_w}" height="54" rx="10" fill="rgba(56,139,253,0.15)" stroke="#388bfd" stroke-width="1.5"/>
      <text x="{pill2_w / 2}" y="22" fill="#58a6ff" font-family="-apple-system, sans-serif" font-size="12" font-weight="800" text-anchor="middle">
        PSYCHOLOGICAL ARCHETYPE VALIDATION
      </text>
      <text x="{pill2_w / 2}" y="42" fill="#8b949e" font-family="-apple-system, sans-serif" font-size="11" text-anchor="middle">
        Real Compat &rho;: {rho_agent:+.2f} vs Internal Consistency &rho;: {cons_rho:+.2f}
      </text>
    </g>
    """

    def y_to_px(val: float) -> float:
        clamped = max(0.0, min(10.0, val))
        return margin_top + bar_area_h - (clamped / 10.0) * bar_area_h

    # Horizontal grid lines
    grid_lines_svg = ""
    for y_val in [0, 2, 4, 6, 8, 10]:
        py = y_to_px(y_val)
        grid_lines_svg += f"""
        <line x1="{margin_left}" y1="{py}" x2="{margin_left + bar_area_w}" y2="{py}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="3,3"/>
        <text x="{margin_left - 10}" y="{py + 4}" fill="#8b949e" font-family="-apple-system, sans-serif" font-size="11" text-anchor="end">{y_val}</text>
        """

    bars_svg = ""
    markers_svg = ""
    labels_svg = ""

    for i, p in enumerate(pairs):
        cx = margin_left + i * group_w + group_w / 2
        y_prior = p["baseline_prior_score"]
        y_agent = p["agent_verdict_score"]
        y_gt = p["ground_truth_score"]

        # Bar 1: Prior (Blue)
        py_prior = y_to_px(y_prior)
        h_prior = (margin_top + bar_area_h) - py_prior
        x_prior = cx - bar_w - 1.5

        # Bar 2: Agent Verdict (Coral/Accent)
        py_agent = y_to_px(y_agent)
        h_agent = (margin_top + bar_area_h) - py_agent
        x_agent = cx + 1.5

        # Ground Truth Marker (Gold Diamond)
        py_gt = y_to_px(y_gt)

        # Label pair abbreviation
        short_a = p["name_a"].split()[0][:5]
        short_b = p["name_b"].split()[0][:5]
        pair_label = html.escape(f"{short_a}×{short_b}")

        bars_svg += f"""
        <g>
          <rect x="{x_prior:.1f}" y="{py_prior:.1f}" width="{bar_w:.1f}" height="{h_prior:.1f}" rx="2" fill="#388bfd" fill-opacity="0.85"/>
          <rect x="{x_agent:.1f}" y="{py_agent:.1f}" width="{bar_w:.1f}" height="{h_agent:.1f}" rx="2" fill="#ff4d6d" fill-opacity="0.9"/>
        </g>
        """

        markers_svg += f"""
        <g>
          <line x1="{cx - bar_w - 4:.1f}" y1="{py_gt:.1f}" x2="{cx + bar_w + 4:.1f}" y2="{py_gt:.1f}" stroke="#ffb703" stroke-width="2.5"/>
          <polygon points="{cx:.1f},{py_gt - 4:.1f} {cx + 4:.1f},{py_gt:.1f} {cx:.1f},{py_gt + 4:.1f} {cx - 4:.1f},{py_gt:.1f}" fill="#ffb703"/>
        </g>
        """

        y_label = margin_top + bar_area_h + 20
        labels_svg += f"""
        <text x="{cx:.1f}" y="{y_label}" fill="#8b949e" font-family="-apple-system, sans-serif" font-size="{label_font_size}" text-anchor="end" transform="rotate(-45, {cx:.1f}, {y_label})">{pair_label}</text>
        """

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {chart_w} {chart_h}" width="100%" height="{chart_h}">
  <rect width="{chart_w}" height="{chart_h}" rx="14" fill="#0d1117" stroke="rgba(255,255,255,0.12)" stroke-width="1.5"/>

  <!-- Title & Subtitle -->
  <text x="36" y="44" fill="#ffffff" font-family="-apple-system, sans-serif" font-size="20" font-weight="800">
    AMORA Conversational Dates vs. Profile-Only Baseline
  </text>
  <text x="36" y="68" fill="#8b949e" font-family="-apple-system, sans-serif" font-size="12">
    Empirical Evaluation: Gold-Standard Ground Truth vs Baseline Prior vs Multi-Turn Agent Verdict ({n} Dyads Across 12 Archetypes)
  </text>

  <!-- Engine Badge -->
  <g transform="translate(36, 84)">
    <rect width="{badge_width}" height="28" rx="6" fill="{engine_bg}" stroke="{engine_stroke}" stroke-width="1.2"/>
    <text x="12" y="18" fill="{engine_color}" font-family="-apple-system, sans-serif" font-size="11" font-weight="700">
      {engine_badge_text}
    </text>
  </g>

  <!-- Metric Badges -->
  {gain_pill2_svg}
  {gain_pill1_svg}

  <!-- Chart Legends -->
  <g transform="translate(36, 126)">
    <!-- Legend 1: Baseline Prior -->
    <rect x="0" y="0" width="14" height="14" rx="3" fill="#388bfd" fill-opacity="0.85"/>
    <text x="22" y="11" fill="#c9d1d9" font-family="-apple-system, sans-serif" font-size="11">Profile Prior (Baseline y0)</text>

    <!-- Legend 2: Agent Verdict -->
    <rect x="180" y="0" width="14" height="14" rx="3" fill="#ff4d6d" fill-opacity="0.9"/>
    <text x="202" y="11" fill="#c9d1d9" font-family="-apple-system, sans-serif" font-size="11">Agent Date Verdict (y_agent)</text>

    <!-- Legend 3: Ground Truth -->
    <polygon points="405,1 411,7 405,13 399,7" fill="#ffb703"/>
    <line x1="395" y1="7" x2="415" y2="7" stroke="#ffb703" stroke-width="2"/>
    <text x="424" y="11" fill="#c9d1d9" font-family="-apple-system, sans-serif" font-size="11">Relational Ground Truth (y*)</text>
  </g>

  <!-- Axes & Grid -->
  {grid_lines_svg}

  <!-- Bars & Markers -->
  {bars_svg}
  {markers_svg}

  <!-- Pair Labels -->
  {labels_svg}
</svg>"""
    return svg
