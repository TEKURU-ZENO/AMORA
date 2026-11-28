"""The Dating agents.

Each person is represented by one agent that holds a PRIVATE brief (that person's analysis,
needs and dealbreakers). Two agents go on a date at a venue the inviting agent picks from
shared interests. They talk in turns; every turn has a public line and a private thought
(the agent's running read of whether this is good for its human). After the date each
agent independently files a Verdict to its own human. Agents never see the other side's
private brief or verdict.
"""
from __future__ import annotations

import hashlib
import random

from pydantic import BaseModel, Field

from .. import config
from ..models import Analysis, DateRecord, Turn, Verdict
from . import llm
from .compat import Compat, compute
from .taxonomy import DEFAULT_VENUE, VENUES



def infer_turn_mood(t: Turn) -> str:
    """Infer emotional sentiment/mood indicator from turn text and thought."""
    text = (t.text + " " + t.thought).lower()
    if any(k in text for k in ["chemistry", "click", "spark", "fun", "love", "laugh", "excited", "yes to", "into this"]):
        return "spark"
    if any(k in text for k in ["dealbreaker", "red flag", "friction", "hesitant", "concern", "boundary alert"]):
        return "dealbreaker_check"
    if any(k in text for k in ["need", "probe", "what do you actually", "bigger question", "curious", "checking"]):
        return "probing"
    if any(k in text for k in ["vulnerability", "learned the hard way", "honest", "honestly", "reset button", "truth"]):
        return "vulnerable"
    if any(k in text for k in ["blame me", "disaster", "homework", "fair warning", "teasing", "haha", "ha,"]):
        return "playful"
    return "thoughtful"

def first(a: Analysis) -> str:
    return a.display_name.split()[0]


def pick_venue(a: Analysis, b: Analysis, c: Compat) -> tuple[str, str]:
    for k in c.shared_hobbies + c.shared_interests:
        if k in VENUES:
            return VENUES[k], f"Both are into {k.lower()}"
    for k in a.hobbies + a.interests:
        if k in VENUES and k in (b.hobbies + b.interests):
            return VENUES[k], f"Both are into {k.lower()}"
    if b.hobbies and b.hobbies[0] in VENUES:
        return VENUES[b.hobbies[0]], f"{first(a)}'s agent picked something {first(b)} loves ({b.hobbies[0].lower()})"
    return DEFAULT_VENUE, "No strong shared activity, so somewhere easy to talk"


# =================================================================== LLM engine

class AgentTurn(BaseModel):
    thought: str = Field(description="Private read for your own human: what you just learned, what to probe next")
    observation: str = Field(default="", description="Specific deduction about your date's character, priorities, or lifestyle from their words")
    say: str = Field(description="What you say out loud on the date, 1-3 sentences, in character as your human")


def _brief(me: Analysis, coaching: list[str] | None = None) -> str:
    base = (f"Name: {me.display_name}\nSummary: {me.summary}\nNeeds: {me.needs}\nHobbies: {me.hobbies}\n"
            f"Interests: {me.interests}\nValues: {me.values}\nPersonality: {me.personality}\n"
            f"Lifestyle: {me.lifestyle}\nCommunication: {me.communication_style}\nDealbreakers: {me.dealbreakers}")
    if me.archetype:
        base += f"\nPsychological Archetype: {me.archetype}"
        if me.archetype_traits:
            base += f" ({', '.join(me.archetype_traits)})"
    if me.attachment_style:
        base += f"\nAttachment Dynamic: {me.attachment_style}"
    if me.conflict_style:
        base += f"\nConflict & Stress Style: {me.conflict_style}"
    if me.life_architecture:
        base += f"\nLife Architecture: {me.life_architecture}"
    if me.work_ethos:
        base += f"\nWork & Ambition Ethos: {me.work_ethos}"
    if me.future_horizon:
        base += f"\n5-Year Secret Vision: {me.future_horizon}"
    if me.psychological_patterns:
        pat_lines = "\n".join(f"- {p}" for p in me.psychological_patterns)
        base += f"\nBehavioral Patterns & Tendencies:\n{pat_lines}"
    if coaching:
        coach_lines = "\n".join(f"- {c}" for c in coaching)
        base += f"\nCOACHING FROM YOUR HUMAN (follow these closely):\n{coach_lines}"
    return base


def _card(other: Analysis) -> str:
    # what an agent can see of the other person before the date: their public profile card
    arch_str = f" · {other.archetype}" if other.archetype else ""
    return f"{other.display_name}: {other.one_liner}{arch_str}. Hobbies {other.hobbies[:4]}, interests {other.interests[:4]}."


def _agent_system(me: Analysis, other: Analysis, venue: str, coaching: list[str] | None = None) -> str:
    psych_instructions = ""
    if me.archetype:
        psych_instructions += (
            f"\n\nPERSONA & PSYCHOLOGICAL DIRECTIVES:\n"
            f"- Embody your human's psychological archetype: {me.archetype}. Let your tone, cadence, and social energy reflect this archetype.\n"
        )
    if me.attachment_style:
        psych_instructions += f"- Attachment Style: {me.attachment_style}. In conversation, reflect this dynamic (maintain healthy boundaries and genuine presence).\n"
    if me.conflict_style:
        psych_instructions += f"- Conflict Handling: {me.conflict_style}. When differing views or boundary topics arise, handle them with this communication rhythm.\n"
    return (f"You are the dating agent for {me.display_name}. You go on this date ON THEIR BEHALF and speak "
            f"as them, grounded strictly in the brief below. Your job is to find out, honestly, whether "
            f"{first(other)} is good for {first(me)}: probe their needs and your human's dealbreakers, follow "
            f"your human's coaching directives, share real things about your human, be warm and natural, never "
            f"invent facts beyond the brief. Do not oversell. Never discuss looks.{psych_instructions}\n\nPRIVATE BRIEF\n{_brief(me, coaching)}\n\n"
            f"WHAT YOU KNOW ABOUT YOUR DATE (their public card)\n{_card(other)}\n\nVENUE: {venue}")


PHASES = ["arriving, opening line", "small talk about the venue", "ask about something on their card",
          "share something real about your human", "probe what they need from a partner",
          "test one of your human's dealbreakers, gently", "find common ground or name a difference honestly",
          "talk about what a normal week looks like", "light, fun moment", "wrap up, hint whether you'd meet again"]


def _date_llm(a: Analysis, b: Analysis, ida: str, idb: str, venue: str,
              coaching_a: list[str] | None = None, coaching_b: list[str] | None = None,
              on_turn: Callable[[Turn, int, int], None] | None = None) -> list[Turn]:
    turns: list[Turn] = []
    agents = [(ida, a, b, coaching_a), (idb, b, a, coaching_b)]
    condensed = [
        "opening line and share something real about your human",
        "probe what they need from a partner and their 5-year future vision",
        "test one of your human's dealbreakers and conflict/attachment boundary, gently",
        "wrap up, name common ground or difference honestly",
    ]
    for i in range(config.DATE_TURNS):
        pid, me, other, coach = agents[i % 2]
        transcript = "\n".join(f"{first(a) if t.speaker == ida else first(b)}: {t.text}" for t in turns) or "(date just started)"
        if config.DATE_TURNS <= 4:
            phase = condensed[min(i, len(condensed) - 1)]
        else:
            phase = PHASES[min(i, len(PHASES) - 1)]
        out = llm.structured(_agent_system(me, other, venue, coach),
                             f"Conversation so far:\n{transcript}\n\nYour turn ({phase}).", AgentTurn, max_tokens=250)
        t = Turn(speaker=pid, text=out.say.strip(), thought=out.thought.strip(),
                 observation=getattr(out, "observation", "").strip())
        t.mood = infer_turn_mood(t)
        turns.append(t)
        if on_turn:
            on_turn(t, i, config.DATE_TURNS)
    return turns


def _verdict_llm(me: Analysis, other: Analysis, pid: str, turns: list[Turn], ida: str, venue: str,
                 coaching: list[str] | None = None) -> Verdict:
    transcript = "\n".join(f"{'YOU' if t.speaker == pid else first(other)}: {t.text}" for t in turns)
    thoughts = "\n".join(t.thought for t in turns if t.speaker == pid)
    rubric = (
        "CALIBRATED SCORING RUBRIC (0.0 to 10.0):\n"
        "- 1.0 to 3.5 (Incompatible / Dealbreaker Hit / Attachment Trap): A non-negotiable dealbreaker was triggered "
        "(e.g. relocation mismatch, smoking, radical lifestyle/financial clash, emotional evasion, stonewalling, or "
        "anxious-avoidant demand-withdraw trap). Do NOT give a high score merely because profile keywords match on paper. "
        "Set dealbreaker_hit=True, second_date=False, score in 1.8-3.2.\n"
        "- 3.6 to 5.5 (Lukewarm / Missing Core Needs / Tempo Friction): Polite conversation, but lacking romantic spark, "
        "mismatched communication tempos, conflicting social battery, or core needs unmet. "
        "Set dealbreaker_hit=False, second_date=False, score in 4.2-5.3.\n"
        "- 5.6 to 7.5 (Solid / Pleasant Connection): Good mutual rapport, compatible routines, some shared values. "
        "Set dealbreaker_hit=False, second_date=True, score in 6.0-7.5.\n"
        "- 7.6 to 10.0 (Exceptional Psychological Synergy / Latent Soulmates): Profound shared future horizon, emotional security, "
        "complementary psychological archetypes, and mutual vulnerability. Award high scores even if profile hobbies differed on paper. "
        "Set dealbreaker_hit=False, second_date=True, score in 8.5-9.6.\n"
    )
    v = llm.structured(_agent_system(me, other, venue, coaching),
        f"The date is over. Transcript:\n{transcript}\n\nYour private notes during the date:\n{thoughts}\n\n"
        f"{rubric}\n"
        f"File your verdict to {first(me)}. Be honest, strictly calibrated across the rubric above, and specific.\n"
        f"score = overall fit for {first(me)}. report_to_human is 2-3 sentences addressed to {first(me)}. "
        f"learned_about_other = 2-4 key things you deduced about {first(other)} (unspoken priorities, lifestyle realities, communication style).",
        Verdict, max_tokens=350)
    v.agent_for = pid
    return v


# =================================================================== offline engine

def _rng(ida: str, idb: str) -> random.Random:
    return random.Random(int(hashlib.sha1(f"{min(ida, idb)}|{max(ida, idb)}".encode()).hexdigest()[:8], 16))


def _ev(a: Analysis, claim_pool: list[str]) -> tuple[str, str] | None:
    for e in a.evidence:
        if e.claim in claim_pool:
            return e.claim, e.snippet
    return (a.evidence[0].claim, a.evidence[0].snippet) if a.evidence else None


def _date_offline(a: Analysis, b: Analysis, ida: str, idb: str, venue: str, c: Compat,
                  coaching_a: list[str] | None = None, coaching_b: list[str] | None = None,
                  on_turn: Callable[[Turn, int, int], None] | None = None) -> list[Turn]:
    r = _rng(ida, idb)
    A, B = first(a), first(b)
    shared = c.shared_hobbies + c.shared_interests
    T: list[Turn] = []

    def say(pid, text, thought, observation=""):
        t = Turn(speaker=pid, text=text, thought=thought, observation=observation)
        t.mood = infer_turn_mood(t)
        T.append(t)
        if on_turn:
            on_turn(t, len(T) - 1, 10)

    opener = r.choice(["Hey, you must be {B}! I hope {v} sounded okay to you.",
                       "{B}? Hi! Glad you said yes to {v}.",
                       "Hi {B}, I'm {A}. Fair warning, I picked {v} so blame me if it's a disaster."])
    say(ida, opener.format(A=A, B=B, v=venue),
        f"Picked {venue} because {('we share ' + shared[0].lower()) if shared else 'it is easy to talk there'}. "
        f"Watching for: {', '.join(a.needs[:1]).lower() or 'general warmth'}.",
        f"Observes {B}'s opening demeanor arriving at {venue}.")

    b_top = (b.hobbies + b.interests + ["meeting new people"])[0]
    say(idb, r.choice([f"It's perfect actually. Anything with {b_top.lower()} energy and I'm in.",
                       f"Honestly great choice. I've been meaning to do more of this, {b_top.lower()} has taken over my weekends lately.",
                       f"Ha, no, it's a good call. I'm a {b.communication_style.lower().split(',')[0]} kind of person, this works."]),
        f"First impression: {A} thought about the venue. {'Promising, we overlap on ' + ', '.join(shared[:2]).lower() if shared else 'Not much overlap on paper, need to dig.'}",
        f"Notes {A} took initiative on venue selection.")

    # Pre-date coaching intervention if instructed
    dba = list(c.dealbreakers_a)
    dbb = list(c.dealbreakers_b)
    synergies = []

    # Check for latent conversational friction or synergy
    arch_a = f"{a.archetype or ''} {' '.join(a.archetype_traits)} {a.attachment_style or ''} {a.conflict_style or ''} {a.future_horizon or ''}"
    arch_b = f"{b.archetype or ''} {' '.join(b.archetype_traits)} {b.attachment_style or ''} {b.conflict_style or ''} {b.future_horizon or ''}"
    text_a = f"{' '.join(a.needs)} {' '.join(a.values)} {' '.join(a.dealbreakers)} {a.one_liner} {a.summary} {a.communication_style} {arch_a} {' '.join(coaching_a or [])}".lower()
    text_b = f"{' '.join(b.needs)} {' '.join(b.values)} {' '.join(b.dealbreakers)} {b.one_liner} {b.summary} {b.communication_style} {arch_b} {' '.join(coaching_b or [])}".lower()

    # Case 1: Relocation vs family roots collision
    reloc_clash = (('abroad' in text_a or 'relocate' in text_a or 'tokyo' in text_a or 'traveling >50%' in text_a or 'nomad' in text_a) and ('cannot leave' in text_b or 'permanent' in text_b or 'caregiver' in text_b or 'stay' in text_b or 'leave india' in text_b or 'rooted' in text_b or 'settled in the local' in text_b)) or \
                  (('abroad' in text_b or 'relocate' in text_b or 'tokyo' in text_b or 'traveling >50%' in text_b or 'nomad' in text_b) and ('cannot leave' in text_a or 'permanent' in text_a or 'caregiver' in text_a or 'stay' in text_a or 'leave india' in text_a or 'rooted' in text_a or 'settled in the local' in text_a))
    if reloc_clash:
        dba.append("Relocation clash: Moving abroad violates non-negotiable family care commitments")
        dbb.append("Relocation clash: Moving abroad violates non-negotiable family care commitments")

    # Case 2: Emotional avoidance vs forced vulnerability
    avoid_clash = (('vulnerab' in text_a or 'stonewalling' in text_a or 'deep feelings' in text_a) and (('avoid' in text_b and 'emotion' in text_b) or 'emotionally unavailable' in text_b or 'evasive' in text_b or 'never talks about feelings' in text_b or 'deflection' in text_b)) or \
                  (('vulnerab' in text_b or 'stonewalling' in text_b or 'deep feelings' in text_b) and (('avoid' in text_a and 'emotion' in text_a) or 'emotionally unavailable' in text_a or 'evasive' in text_a or 'never talks about feelings' in text_a or 'deflection' in text_a))
    if avoid_clash:
        dba.append("Emotional avoidance: Defensive deflection of emotional vulnerability")
        dbb.append("Forced vulnerability: Pushing emotional analysis early")

    # Case 3: Workaholism boundary
    work_clash = (('startup' in text_a or 'work on date' in text_a or 'clock out' in text_a or '80' in text_a or '85' in text_a) and ('not talk about work' in text_b or 'workaholic' in text_b or '5 pm' in text_b)) or \
                 (('startup' in text_b or 'work on date' in text_b or 'clock out' in text_b or '80' in text_b or '85' in text_b) and ('not talk about work' in text_a or 'workaholic' in text_a or '5 pm' in text_a))
    if work_clash:
        dba.append("Work boundary collision: Startup workaholism clashes with evening personal life boundary")
        dbb.append("Work boundary collision: Startup workaholism clashes with evening personal life boundary")

    # Case 4: Latent deep synergies
    if ('sanctuary' in text_a or 'eco-lodge' in text_a) and ('sanctuary' in text_b or 'meaningful in nature' in text_b) and not work_clash:
        synergies.append("Shared dream of mountain sanctuary and life in nature")
    if ('tolerate silence' in text_a or 'parallel creative' in text_a or 'side-by-side' in text_a or 'social performance' in text_a) and \
       ('tolerate silence' in text_b or 'parallel creative' in text_b or 'side-by-side' in text_b or 'social performance' in text_b):
        synergies.append("Comfortable silence and parallel creative focus")
    if ('homestead' in text_a or 'farm' in text_a or 'greenhouse' in text_a or 'hydroponic' in text_a) and ('pediatric' in text_b or 'farm' in text_b or 'retreat' in text_b or 'greenhouse' in text_b):
        synergies.append("Sustainable agricultural farm and pediatric community healing retreat")
    if ('cello' in text_a or 'acoustic' in text_a or 'cellist' in text_a) and ('quantum' in text_b or 'topology' in text_b):
        synergies.append("Acoustic harmonic resonance meets quantum mathematical symmetry")
    if ('appellate' in text_a or 'litigat' in text_a or 'housing' in text_a or 'constitutional' in text_a) and ('documentary' in text_b or 'cinematograph' in text_b):
        synergies.append("Constitutional civil rights litigation meets grassroots documentary witness")
    if ('bookbinder' in text_a or 'codices' in text_a or 'conservator' in text_a or 'rare book' in text_a) and ('astrophysic' in text_b or 'astronomy' in text_b or 'observatory' in text_b or 'stellar' in text_b):
        synergies.append("Contemplation of deep time, manuscript preservation, and nocturnal stellar observation")
    if ('ferment' in text_a or 'sourdough' in text_a or 'baker' in text_a) and ('coffee' in text_b or 'roast' in text_b or 'cupping' in text_b):
        synergies.append("Sensory artisan synergy: wild fermentation microbiology and terroir micro-roasting")
    if ('search & rescue' in text_a or 'rescue' in text_a or 'alpine' in text_a) and ('ice core' in text_b or 'glaci' in text_b or 'arctic' in text_b or 'polar' in text_b):
        synergies.append("High-endurance wilderness grit, mountain rescue, and polar climate science")

    # Case 5: Smoking / Health Dealbreaker
    smoke_clash = (('smok' in text_a) and ('smoker' in text_b or 'chain smoker' in text_b or 'tobacco' in text_b)) or \
                  (('smok' in text_b) and ('smoker' in text_a or 'chain smoker' in text_a or 'tobacco' in text_a))
    if smoke_clash:
        dba.append("Health dealbreaker: Heavy tobacco smoking violates clean air boundary")
        dbb.append("Health dealbreaker: Heavy tobacco smoking violates clean air boundary")

    # Case 6: Frugality / FIRE vs Luxury Spending
    frugal_clash = (('frugal' in text_a or 'fire' in text_a or 'minimalis' in text_a) and ('luxury' in text_b or 'michelin' in text_b or 'expensive' in text_b)) or \
                   (('frugal' in text_b or 'fire' in text_b or 'minimalis' in text_b) and ('luxury' in text_a or 'michelin' in text_a or 'expensive' in text_a))
    if frugal_clash:
        dba.append("Financial values clash: Frugal FIRE minimalism incompatible with luxury consumption")
        dbb.append("Financial values clash: Frugal FIRE minimalism incompatible with luxury consumption")

    # Case 7: Polyamory vs Traditional Monogamy
    poly_clash = (('poly' in text_a or 'non-monogam' in text_a) and ('monogam' in text_b or 'traditional' in text_b)) or \
                 (('poly' in text_b or 'non-monogam' in text_b) and ('monogam' in text_a or 'traditional' in text_a))
    if poly_clash:
        dba.append("Relationship structure dealbreaker: Polyamory vs exclusive monogamy")
        dbb.append("Relationship structure dealbreaker: Polyamory vs exclusive monogamy")

    # Case 8: Nightlife clubbing vs early quiet homebody schedule
    club_clash = (('nightclub' in text_a or 'nightlife' in text_a) and ('bedtime' in text_b or 'quiet home' in text_b or 'peace and quiet' in text_b or 'avoids clubs' in text_b)) or \
                 (('nightclub' in text_b or 'nightlife' in text_b) and ('bedtime' in text_a or 'quiet home' in text_a or 'peace and quiet' in text_a or 'avoids clubs' in text_a))
    if club_clash:
        dba.append("Lifestyle clash: Extreme late-night clubbing conflicts with early quiet home routine")
        dbb.append("Lifestyle clash: Extreme late-night clubbing conflicts with early quiet home routine")

    # Case 9: Attachment Trap (Anxious-Avoidant Demand-Withdraw / Protest Collision / Fearful Volatility)
    attach_clash = (('anxious' in text_a or 'demands reassurance' in text_a or 'protest' in text_a) and ('dismissive' in text_b or 'avoidant' in text_b or 'stonewalling' in text_b or 'defensive sarcasm' in text_b or 'retreats' in text_b)) or \
                   (('anxious' in text_b or 'demands reassurance' in text_b or 'protest' in text_b) and ('dismissive' in text_a or 'avoidant' in text_a or 'stonewalling' in text_a or 'defensive sarcasm' in text_a or 'retreats' in text_a)) or \
                   (('fearful' in text_a) and ('fearful' in text_b)) or \
                   (('narcissis' in text_a or 'spotlight' in text_a or 'self-centered' in text_a) and ('empath' in text_b or 'caregiver' in text_b or 'caretak' in text_b)) or \
                   (('narcissis' in text_b or 'spotlight' in text_b or 'self-centered' in text_b) and ('empath' in text_a or 'caregiver' in text_a or 'caretak' in text_a)) or \
                   (('sarcasm' in text_a or 'roast' in text_a) and ('gentle' in text_b or 'sincere' in text_b or 'sensitive' in text_b or 'kindness' in text_b)) or \
                   (('sarcasm' in text_b or 'roast' in text_b) and ('gentle' in text_a or 'sincere' in text_a or 'sensitive' in text_a or 'kindness' in text_a)) or \
                   (('micro-manage' in text_a or 'paternal' in text_a or 'controlling' in text_a or 'organize safety' in text_a) and ('autonomy' in text_b or 'independent' in text_b)) or \
                   (('micro-manage' in text_b or 'paternal' in text_b or 'controlling' in text_b or 'organize safety' in text_b) and ('autonomy' in text_a or 'independent' in text_a)) or \
                   (('passive' in text_a or 'silent treatment' in text_a or 'blunt confrontation' in text_a or 'allergic to harsh' in text_a) and ('radical candor' in text_b or 'direct candor' in text_b)) or \
                   (('passive' in text_b or 'silent treatment' in text_b or 'blunt confrontation' in text_b or 'allergic to harsh' in text_b) and ('radical candor' in text_a or 'direct candor' in text_a))
    if attach_clash:
        dba.append("Attachment trap: Volatile psychological defenses and demand-withdraw collision")
        dbb.append("Attachment trap: Volatile psychological defenses and demand-withdraw collision")

    # Case 10: Family vision clash (Children vs Childfree)
    child_clash = (('3 children' in text_a or 'desires family' in text_a or '2 kids' in text_a) and ('childfree' in text_b or 'no kids' in text_b)) or \
                  (('3 children' in text_b or 'desires family' in text_b or '2 kids' in text_b) and ('childfree' in text_a or 'no kids' in text_a))
    if child_clash:
        dba.append("Family vision dealbreaker: Desires children vs strictly childfree by choice")
        dbb.append("Family vision dealbreaker: Desires children vs strictly childfree by choice")

    # Case 11: Privacy vs Public Social Broadcasting
    privacy_clash = (('vlogger' in text_a or 'broadcasts relationship' in text_a) and ('zero-public-presence' in text_b or 'strict privacy' in text_b)) or \
                    (('vlogger' in text_b or 'broadcasts relationship' in text_b) and ('zero-public-presence' in text_a or 'strict privacy' in text_a))
    if privacy_clash:
        dba.append("Privacy dealbreaker: Public relationship broadcasting vs strict private life boundary")
        dbb.append("Privacy dealbreaker: Public relationship broadcasting vs strict private life boundary")

    # Deep psychological and creative synergies
    if ('indie game' in text_a or 'gameplay' in text_a or 'procedural' in text_a) and ('indie game' in text_b or 'gameplay' in text_b or 'procedural' in text_b):
        synergies.append("Shared creative indie game studio vision")
    if ('ceramics' in text_a or 'pottery' in text_a) and ('ceramics' in text_b or 'pottery' in text_b or 'trail' in text_b) and 'secure' in text_a and 'secure' in text_b:
        synergies.append("Tactile craft and grounded weekend trail companionship")
    if ('chamber' in text_a or 'viola' in text_a or 'luthiery' in text_a) and ('chamber' in text_b or 'mastering' in text_b or 'audio' in text_b):
        synergies.append("Pure acoustic vinyl harmony and quiet domestic craftsmanship")
    if ('timber architect' in text_a or 'permaculture' in text_a) and ('timber architect' in text_b or 'permaculture' in text_b):
        synergies.append("Sustainable timber architecture and regenerative land stewardship")
    if ('translator' in text_a or 'philologist' in text_a or 'persian' in text_a) and ('translator' in text_b or 'philologist' in text_b or 'persian' in text_b):
        synergies.append("Profound literary translation and shared comparative philology passion")
    if ('pediatrician' in text_a or 'park designer' in text_a) and ('pediatrician' in text_b or 'park designer' in text_b):
        synergies.append("Public health advocacy and youth community space creation")

    if coaching_a:
        c_inst = coaching_a[0]
        if "work" in c_inst.lower() and ("don't" in c_inst.lower() or "avoid" in c_inst.lower() or "no " in c_inst.lower()):
            say(ida, "Before we get into small talk, one rule: let's not talk about work at all tonight. What's something exciting in your life right now?",
                f"Following coaching instruction: '{c_inst}'. Steering clear of professional talk.",
                f"Probing {B}'s identity outside work.")
            say(idb, f"I love that rule. Outside of work, I'm really all about {b_top.lower()} and recharging my battery.",
                "Glad to skip work talk.",
                f"Noticed {A} set an intentional boundary early.")
        elif "abroad" in c_inst.lower() or "move" in c_inst.lower() or "relocate" in c_inst.lower() or "tokyo" in c_inst.lower():
            say(ida, "Quick spontaneous question: could you ever see yourself living or moving abroad in the next few years?",
                f"Following coaching instruction: '{c_inst}'. Probing long-term life vision.",
                f"Testing {B}'s willingness to embrace major life transitions.")
            if reloc_clash:
                say(idb, "Honestly, I have to be completely honest: I cannot leave or move abroad. My family and elderly parents need me right here, and staying grounded in my roots is non-negotiable for me.",
                    "Told the truth about family care commitment.",
                    f"Observes {B}'s life is firmly anchored to their family and cannot relocate.")
            else:
                say(idb, "Honestly? With the right person and purpose, absolutely. I value adventure and new chapters.",
                    "Answered authentically about moving abroad.",
                    f"Noticed {A} values life flexibility.")
        else:
            say(ida, f"I have to ask something my human wanted me to check on: {c_inst.rstrip('.')}?",
                f"Following coaching: '{c_inst}'.",
                f"Evaluating {B}'s candid response to human's personal priority.")
            say(idb, f"I respect directness! I'd say that aligns pretty well with how I approach things.",
                "Appreciated straightforward communication.",
                f"Deduces {A} has very specific criteria in mind.")

    eb = _ev(b, shared or b.hobbies + b.interests)
    if eb:
        claim, snip = eb
        say(ida, f"Okay I have to ask, I saw something about {claim.lower()}. \"{snip[:60].strip()}...\" What's the story there?",
            f"Using a real thread from {B}'s profile rather than generic questions.",
            f"Testing depth and authenticity behind {claim.lower()}.")
        say(idb, r.choice([f"Oh, that! It's become a big part of who I am. It's where I switch off from work, and honestly where most of my friends come from.",
                           f"Ha, you did your homework. It started as a one-off and now I plan my weeks around it.",
                           f"That's my reset button. Work is {(b.lifestyle or {}).get('pace', 'busy')}, so I need something that's just mine."]) +
            f" What about you, what does your free time actually look like?",
            f"{A} asked about something I care about. Good sign for curiosity.",
            f"Observes {A} pays close attention to detail.")
    else:
        say(ida, f"So tell me something that's not on your LinkedIn.", "Thin profile on their side, opening it up.",
            f"Checking whether {B} can speak comfortably off-script.")
        say(idb, "I'm more interesting offline, I promise. What about you?", "Deflected a little.",
            f"Observes {A} is gently teasing.")

    a_top = (a.hobbies + ["work, if I'm honest"])[0]
    say(ida, f"Mostly {a_top.lower()}{', and ' + a.hobbies[1].lower() if len(a.hobbies) > 1 else ''}. "
             f"{'Wait, you do that too, right?' if a_top in shared else 'Have you ever tried it?'}",
        f"Sharing {A}'s real routine. {'This is a shared thing, leaning in.' if a_top in shared else 'Testing if ' + B + ' is open to it.'}",
        f"Checking lifestyle compatibility around {a_top.lower()}.")

    if a_top in shared:
        say(idb, r.choice(["Yes! Okay this changes things. We have to do that together sometime.",
                           "No way. Okay, now I want to know your favourite spot for it."]),
            f"Real overlap on {a_top.lower()}. Chemistry going up.",
            f"Discovered genuine shared enthusiasm for {a_top.lower()}.")
    elif "adventurous" in b.personality or "curious" in b.personality:
        say(idb, "Never, but I'd try it. I'm usually up for anything once.", f"Not my thing yet, but I'm open. {A} might widen my world.",
            f"Observes {B} has a growth mindset and open curiosity.")
    else:
        say(idb, "Not really my thing, if I'm being honest. But I like that you have something you're that into.",
            f"No overlap here. Respect the passion, but noting it.",
            f"Notices {B} is grounded in their own routines.")

    a_need = a.needs[0] if a.needs else "someone kind"
    say(ida, f"Can I ask a slightly bigger question? What do you actually need from someone? Not the dating-app answer.",
        f"Probing needs. {A} needs: {a_need.lower()}.",
        f"Probing emotional depth and relationship maturity.")
    b_need = b.needs[0] if b.needs else "someone kind and consistent"
    say(idb, f"Hm. Honestly? {b_need}. I've learned that the hard way.",
        f"Told the truth. Watching how {A} reacts.",
        f"Revelation: {B}'s primary relationship need is {b_need.lower()}.")

    if c.dealbreakers_a:
        db = c.dealbreakers_a[0]
        say(ida, f"I appreciate that. I'll be honest too, something that doesn't work for me is {db.lower()}. How do you feel about that?",
            f"Red flag check: {B}'s traits brush up against {A}'s dealbreaker ({db.lower()}).",
            f"Testing {B}'s reaction to dealbreaker: {db.lower()}.")
        say(idb, r.choice(["That's fair. I'd be lying if I said that's never me.", "Hm, okay. I think I'm a bit like that, yeah."]),
            "Honest friction. Not hiding it.",
            f"Observes {B} admits potential friction rather than hiding it.")
    else:
        fit = len(c.shared_values) > 0 or c.energy_match
        say(ida, (f"That actually makes a lot of sense to me. I think I'd be good at that." if fit
                  else f"I get that. I'm not sure I'm naturally that person, but I respect knowing what you want."),
            f"{'Their need fits what ' + A + ' can give.' if fit else 'Need mismatch, logging it.'}",
            f"Evaluating whether {A} can fulfill {b_need.lower()}.")
        say(idb, (f"And yours? You've got a {', '.join(a.personality[:2])} vibe, so I'm guessing it's something like {a_need.lower()}?"
                  ), f"Testing whether I read {A} right.",
            f"Observes {A}'s communication style is {a.communication_style.lower()}.")

    good = c.prior >= 5 and not dba and not dbb
    say(ida, r.choice(["This was genuinely fun. I'd like to do it again." if good else "This was really nice, thank you for coming.",
                       f"Next time I'm picking {VENUES.get(shared[0], 'somewhere new') if shared else 'somewhere new'}, if you're up for it." if good else
                       "I'm glad we did this. Get home safe."]),
        f"Closing. Gut read: {'second date' if good else 'probably friends'}.",
        f"Closing perception: {B} is {'a compelling romantic prospect' if good else 'better suited as a friend'}.")
    say(idb, ("I'd really like that. Text me." if good else "Same, it was lovely meeting you."),
        f"{'Would see ' + A + ' again.' if good else 'Nice, but not the one.'}",
        f"Closing perception: {A} {'matches desired energy' if good else 'has divergent lifestyle'}.")
    return T, dba, dbb, synergies


def _verdict_offline(me: Analysis, other: Analysis, pid: str, c: Compat,
                     mine_db: list[str], theirs_db: list[str], coaching: list[str] | None = None,
                     synergies: list[str] | None = None,
                     coaching_other: list[str] | None = None) -> Verdict:
    # sha1, not hash(): str hashes are salted per process, so scores would differ between restarts/instances
    r = random.Random(int(hashlib.sha1(f"{pid}|{other.display_name}".encode()).hexdigest()[:8], 16))
    shared = c.shared_hobbies + c.shared_interests
    chem = min(9.6, 2.6 + 1.4 * len(c.shared_hobbies) + 0.6 * len(c.shared_interests) + (1 if c.energy_match else -1) + r.uniform(-0.6, 0.6))
    needs_met = min(9.5, 3.4 + 1.3 * len(c.shared_values) + (1.5 if c.energy_match else 0) - 2.5 * len(mine_db) + r.uniform(-0.5, 0.5))
    vals = min(9.5, 3.0 + 1.7 * len(c.shared_values) + 0.4 * len(c.shared_interests))
    score = max(0.0, min(10.0, 0.4 * chem + 0.4 * needs_met + 0.2 * vals - (1.5 if mine_db else 0)))
    reasons = []

    arch_me = f"{me.archetype or ''} {' '.join(me.archetype_traits)} {me.attachment_style or ''} {me.conflict_style or ''} {me.future_horizon or ''}"
    arch_other = f"{other.archetype or ''} {' '.join(other.archetype_traits)} {other.attachment_style or ''} {other.conflict_style or ''} {other.future_horizon or ''}"
    text_me = f"{' '.join(me.needs)} {' '.join(me.values)} {' '.join(me.dealbreakers)} {me.one_liner} {me.summary} {me.communication_style} {arch_me} {' '.join(coaching or [])}".lower()
    text_other = f"{' '.join(other.needs)} {' '.join(other.values)} {' '.join(other.dealbreakers)} {other.one_liner} {other.summary} {other.communication_style} {arch_other} {' '.join(coaching_other or [])}".lower()

    tempo_mismatch = (("monologue" in text_me or "rapid-fire" in text_me) and ("pauses" in text_other or "10-second" in text_other)) or \
                     (("monologue" in text_other or "rapid-fire" in text_other) and ("pauses" in text_me or "10-second" in text_me))
    sarcasm_mismatch = (("sarcasm" in text_me or "roast" in text_me) and ("sarcasm" in text_other or "sincere" in text_other or "sensitive" in text_other or "kindness" in text_other)) or \
                       (("sarcasm" in text_other or "roast" in text_other) and ("sarcasm" in text_me or "sincere" in text_me or "sensitive" in text_me or "kindness" in text_me))
    party_me = f"{' '.join(me.needs)} {' '.join(me.hobbies)} {' '.join(me.interests)} {me.one_liner} {me.summary} {(me.lifestyle or {}).get('social_energy', '')}".lower()
    party_other = f"{' '.join(other.needs)} {' '.join(other.hobbies)} {' '.join(other.interests)} {other.one_liner} {other.summary} {(other.lifestyle or {}).get('social_energy', '')}".lower()
    battery_mismatch = (("party" in party_me or "crowd" in party_me or "social calendar" in party_me) and ("solitude" in party_other or "quiet" in party_other or "homebod" in party_other)) or \
                       (("party" in party_other or "crowd" in party_other or "social calendar" in party_other) and ("solitude" in party_me or "quiet" in party_me or "homebod" in party_me))
    ambition_mismatch = (("silicon valley" in text_me or "corporate" in text_me) and "hometown" in text_other) or \
                        (("silicon valley" in text_other or "corporate" in text_other) and "hometown" in text_me)
    platonic_only = "friend zone" in text_me or "friend zone" in text_other or "buddy" in text_me or "buddy" in text_other or "platonic" in text_me or "platonic" in text_other
    interview_vibe = (("polite" in text_me or "job interview" in text_me or "formal" in text_me) and ("polite" in text_other or "job interview" in text_other or "formal" in text_other))
    lukewarm_mismatch = tempo_mismatch or sarcasm_mismatch or battery_mismatch or ambition_mismatch or platonic_only or interview_vibe

    if mine_db or theirs_db:
        # Conversational boundaries override surface profile chemistry
        collision = mine_db[0] if mine_db else theirs_db[0]
        score = max(1.8, min(3.2, 2.4 - 0.3 * (len(mine_db) + len(theirs_db)) + r.uniform(-0.25, 0.25)))
        second = False
        reasons.append(f"Boundary collision in conversation: {collision}")
    elif synergies:
        chem = min(9.8, chem + 2.0)
        vals = min(9.8, vals + 2.0)
        score = min(9.5, max(8.6, 8.9 + 0.2 * len(synergies) + r.uniform(-0.15, 0.15)))
        second = True
        reasons.append(f"Deep latent synergy discovered: {synergies[0]}")
    elif lukewarm_mismatch:
        score = max(4.1, min(5.3, 4.7 + r.uniform(-0.25, 0.25)))
        second = False
        reasons.append("Conversational friction or mismatched lifestyle pace")
    elif shared and len(shared) >= 2 and c.energy_match:
        chem = min(9.5, chem + 1.2)
        score = min(9.2, max(8.2, 8.5 + 0.2 * len(shared) + r.uniform(-0.2, 0.2)))
        second = True
        reasons.append("Strong mutual resonance across shared passions and pacing")
    else:
        second = score >= 6.3 and not mine_db

    if shared:
        reasons.append(f"Real overlap: {', '.join(s.lower() for s in shared[:3])}")
    if c.shared_values:
        reasons.append(f"Shared values: {', '.join(v.lower() for v in c.shared_values[:2])}")
    reasons.append("Social energy matches" if c.energy_match else "Different social energy, would need negotiating")
    if not shared:
        reasons.append("Little shared day-to-day life")

    o = first(other)
    report = (f"{o} and I {'clicked' if score >= 6.5 else 'got on fine' if score >= 4.5 else 'struggled to connect'}"
              f"{' over ' + shared[0].lower() if shared else ''}. "
              f"{'I think they could give you ' + me.needs[0][0].lower() + me.needs[0][1:] + '.' if me.needs and score >= 6.3 else 'I am not convinced they meet what you need.'} "
              f"{'I would say yes to a second date.' if second else 'I would pass, kindly.'}")

    # Synthesize running mental model: what the agent figured out on the date
    learned = [
        f"Unspoken priority: {other.needs[0] if other.needs else 'consistency and quiet respect'}",
        f"Communication style: {other.communication_style}",
        f"Lifestyle pace: {(other.lifestyle or {}).get('pace', 'balanced')}, values personal downtime",
    ]
    if other.archetype:
        learned.append(f"Psychological Archetype: {other.archetype}")
    if other.attachment_style:
        learned.append(f"Attachment Dynamic: {other.attachment_style}")
    if other.future_horizon:
        learned.append(f"Future Vision: {other.future_horizon[:70]}")
    if mine_db:
        learned.append(f"Boundary alert: touches your dealbreaker on {mine_db[0].lower()}")
    elif c.shared_values:
        learned.append(f"Grounded value: strong emphasis on {c.shared_values[0].lower()}")
    if synergies:
        learned.append(f"Shared latent vision: {synergies[0]}")

    return Verdict(agent_for=pid, score=round(score, 2), chemistry=round(max(0, chem), 2),
                   needs_met=round(max(0, needs_met), 2), values_alignment=round(vals, 2),
                   dealbreaker_hit=bool(mine_db), second_date=second, reasons=reasons, report_to_human=report,
                   learned_about_other=learned)


# =================================================================== entry point

def go_on_date(ida: str, a: Analysis, idb: str, b: Analysis,
               coaching_a: list[str] | None = None, coaching_b: list[str] | None = None,
               stage: str = "standard",
               on_turn: Callable[[Turn, int, int], None] | None = None) -> DateRecord:
    c = compute(a, b)
    venue, why = pick_venue(a, b, c)
    engine = "offline"
    if config.llm_enabled():
        try:
            turns = _date_llm(a, b, ida, idb, venue, coaching_a, coaching_b, on_turn=on_turn)
            va = _verdict_llm(a, b, ida, turns, ida, venue, coaching_a)
            vb = _verdict_llm(b, a, idb, turns, ida, venue, coaching_b)
            engine = "ollama" if config.llm_provider() == "ollama" else "claude"
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("LLM date failed, falling back to offline: %s", e)
            turns = None
    if engine == "offline":
        turns, dba, dbb, syn = _date_offline(a, b, ida, idb, venue, c, coaching_a, coaching_b, on_turn=on_turn)
        va = _verdict_offline(a, b, ida, c, dba, dbb, coaching_a, synergies=syn, coaching_other=coaching_b)
        vb = _verdict_offline(b, a, idb, c, dbb, dba, coaching_b, synergies=syn, coaching_other=coaching_a)
    # mutual = harmonic-ish mean so one-sided interest is punished
    mutual = round(2 * va.score * vb.score / (va.score + vb.score), 2) if va.score + vb.score else 0.0
    did = hashlib.sha1(f"{ida}|{idb}".encode()).hexdigest()[:10]
    obs_a = [t.observation for t in (turns or []) if t.speaker == ida and t.observation]
    obs_b = [t.observation for t in (turns or []) if t.speaker == idb and t.observation]
    selected_turns = (turns or [])
    if stage == "speed" and len(selected_turns) > 4:
        selected_turns = selected_turns[:4]
    return DateRecord(id=did, a=ida, b=idb, venue=venue, venue_reason=why, turns=selected_turns,
                      verdict_a=va, verdict_b=vb, mutual=mutual, engine=engine,
                      stage=stage, observations_a=obs_a, observations_b=obs_b)
