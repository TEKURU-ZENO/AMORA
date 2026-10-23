"""The "First Fight" Scenario Engine: Compatibility Under Stress.

Simulates how two agents navigate high-stakes tension after a successful first date:
- Career opportunities / relocation dilemmas
- Weekend social commitments vs solitary recharge
- Financial philosophies and lifestyle spending
- Opposing conflict regulation styles (withdrawal vs immediate processing)

Produces turn-by-turn dialogue, emotional tone tracking, conflict repair attempts,
and a Resilience Verdict evaluating communication under pressure.
"""
from __future__ import annotations

import hashlib
import random
from typing import Literal

from pydantic import BaseModel, Field

from .. import config
from ..models import Analysis, DateRecord, FirstFightRecord, Person, StressTurn, StressVerdict
from . import llm
from .compat import compute


def first(a: Analysis) -> str:
    return a.display_name.split()[0]


SCENARIOS = [
    {
        "id": "relocation",
        "title": "The Relocation Dilemma: Career Ambition vs Proximity",
        "prompt": (
            "One partner receives an unexpected, career-defining opportunity in another city requiring a decision within two weeks. "
            "How do you communicate uncertainty, personal ambitions, and long-term commitment without resentment?"
        ),
        "trigger": lambda a, b: "career" in str(a.lifestyle).lower() or "travel" in str(b.lifestyle).lower() or len(a.dealbreakers) > 1,
    },
    {
        "id": "weekend_clash",
        "title": "The Energy Clash: Packed Social Weekend vs Solitary Recharge",
        "prompt": (
            "After an exhausting work week, one partner enthusiastically booked a full weekend of social gatherings with friends, "
            "while the other is depleted and desperately needs quiet recharge time at home. How do you navigate boundaries without guilt?"
        ),
        "trigger": lambda a, b: (a.lifestyle or {}).get("social energy") != (b.lifestyle or {}).get("social energy"),
    },
    {
        "id": "financial_habits",
        "title": "Financial Philosophies: Spontaneous Experiences vs Long-Term Security",
        "prompt": (
            "While planning a shared milestone trip, contrasting money habits surface: one prioritizes spontaneous luxury and enjoying "
            "the moment, while the other insists on strict budgeting and financial conservatism. How do you resolve differing value priorities?"
        ),
        "trigger": lambda a, b: any("money" in d.lower() or "security" in d.lower() for d in a.dealbreakers + b.dealbreakers),
    },
    {
        "id": "communication_style",
        "title": "Under Pressure: Emotional Withdrawal vs Immediate Processing",
        "prompt": (
            "A stressful misunderstanding triggers opposing conflict instincts: one person instinctively needs space to cool down, "
            "while the other feels intensely anxious and pushes for immediate resolution. How do you de-escalate and bridge the gap?"
        ),
        "trigger": lambda a, b: True,  # Universal fallback
    },
]


def pick_scenario(a: Analysis, b: Analysis) -> tuple[str, str]:
    for s in SCENARIOS:
        if s["trigger"](a, b):
            return s["title"], s["prompt"]
    s = SCENARIOS[-1]
    return s["title"], s["prompt"]


# =================================================================== LLM Engine

class StressTurnOutput(BaseModel):
    speaker: str
    say: str = Field(description="1-3 sentences spoken under tension, true to your human's temperament")
    thought: str = Field(description="Inner emotional reaction: feeling defensive, misunderstood, or empathetic")
    emotional_tone: str = Field(description="Emotional tone: empathetic, defensive, conciliatory, firm, collaborative, curious, or guarded")


class StressVerdictOutput(BaseModel):
    resilience_score: float = Field(ge=0, le=10, description="0-10 score of how productively the relationship absorbed stress")
    resolution_style: str = Field(description="e.g. empathetic compromise, anxious appeasement, collaborative problem-solving, rigid boundary-setting")
    stress_verdict: Literal["passed", "conditional", "failed"] = Field(description="passed = grew closer; conditional = workable with care; failed = dealbreaker")
    key_takeaway: str = Field(description="2-3 sentence reflection on how your partner handled conflict and what it means for your human")
    growth_potential: str = Field(description="Short outlook on future emotional safety with this partner")


def _simulate_llm(pa: Person, pb: Person, did: str, title: str, prompt: str) -> tuple[list[StressTurn], StressVerdict, StressVerdict]:
    a, b = pa.analysis, pb.analysis
    ida, idb = pa.id, pb.id
    turns: list[StressTurn] = []
    agents = [(ida, a, b), (idb, b, a)]

    system_prompt_template = (
        "You are representing {me_name} in a realistic relationship stress-test scenario. "
        "Your human's brief: Needs: {needs}, Values: {values}, Dealbreakers: {dealbreakers}, Communication: {comm}. "
        "Scenario: {title} - {scenario_prompt}. "
        "Speak in character. Do not be overly agreeable or artificially polite. Represent genuine emotional boundaries, "
        "vulnerabilities, and communication tendencies."
    )

    for i in range(6):
        pid, me, other = agents[i % 2]
        history = "\n".join(f"{t.speaker}: {t.text} (tone: {t.emotional_tone})" for t in turns) or "(Conflict scenario just started)"
        sys_p = system_prompt_template.format(
            me_name=me.display_name,
            needs=me.needs,
            values=me.values,
            dealbreakers=me.dealbreakers,
            comm=me.communication_style,
            title=title,
            scenario_prompt=prompt
        )
        user_p = f"Dialogue so far:\n{history}\n\nYour turn (Turn {i+1} of 6). Respond to the conflict constructively or voice your concern honestly."
        out = llm.structured(sys_p, user_p, StressTurnOutput, max_tokens=450)
        turns.append(StressTurn(
            speaker=pid,
            text=out.say.strip(),
            thought=out.thought.strip(),
            emotional_tone=out.emotional_tone.strip().lower()
        ))

    def evaluate(me: Analysis, other: Analysis, pid: str) -> StressVerdict:
        history = "\n".join(f"{t.speaker}: {t.text}" for t in turns)
        sys_p = (
            f"You are the conflict psychologist agent for {me.display_name}. "
            f"Review the 6-turn stress conversation below and evaluate how {first(other)} and {first(me)} handled friction."
        )
        user_p = f"Transcript:\n{history}\n\nFile your stress verdict."
        v = llm.structured(sys_p, user_p, StressVerdictOutput, max_tokens=600)
        return StressVerdict(
            agent_for=pid,
            resilience_score=round(v.resilience_score, 1),
            resolution_style=v.resolution_style,
            stress_verdict=v.stress_verdict,
            key_takeaway=v.key_takeaway,
            growth_potential=v.growth_potential
        )

    va = evaluate(a, b, ida)
    vb = evaluate(b, a, idb)
    return turns, va, vb


# =================================================================== Offline Simulation

def _simulate_offline(pa: Person, pb: Person, did: str, title: str, prompt: str) -> tuple[list[StressTurn], StressVerdict, StressVerdict]:
    a, b = pa.analysis, pb.analysis
    ida, idb = pa.id, pb.id
    c = compute(a, b)
    A, B = first(a), first(b)

    # Seed deterministic RNG
    seed = int(hashlib.sha1(f"stress|{min(ida, idb)}|{max(ida, idb)}|{title}".encode()).hexdigest()[:8], 16)
    r = random.Random(seed)

    turns: list[StressTurn] = []

    if "Relocation" in title:
        turns.append(StressTurn(
            speaker=ida,
            text=f"I wanted to be open with you early: I just heard about a career opportunity in another city that would demand a move in the near future. It's a huge step for me, but I didn't want to hide it from where this might go.",
            thought=f"Scared of scaring {B} off, but my human values transparency and ambition.",
            emotional_tone="vulnerable"
        ))
        turns.append(StressTurn(
            speaker=idb,
            text=f"Thank you for being upfront. My immediate gut reaction is that distance is tough, especially when we're just getting to know each other. I'd need to know if you see room for us or if work always dictates the map.",
            thought=f"Appreciate the honesty, but testing whether {A} considers a partner in life pivots.",
            emotional_tone="firm"
        ))
        turns.append(StressTurn(
            speaker=ida,
            text=f"That's completely valid. For me, ambition matters, but so does building something meaningful. If we felt this was real, I'd want a plan that supports both of us, not just unilateral decisions.",
            thought=f"Validating {B}'s boundary. Proving partnership isn't an afterthought.",
            emotional_tone="empathetic"
        ))
        turns.append(StressTurn(
            speaker=idb,
            text=f"Hearing that you see it as a shared conversation makes a big difference. I don't want someone to sacrifice their dreams, but I need clear communication and intentional time together.",
            thought=f"{A} didn't get defensive. Huge green flag for emotional safety.",
            emotional_tone="collaborative"
        ))
        turns.append(StressTurn(
            speaker=ida,
            text=f"Agreed. Let's take it step by step, keep talking without pressure, and ensure we're never making assumptions for the other person.",
            thought=f"De-escalated without compromising my human's goals. Solid mutual respect.",
            emotional_tone="conciliatory"
        ))
        turns.append(StressTurn(
            speaker=idb,
            text=f"Deal. Navigating this conversation without tension actually makes me trust you more.",
            thought=f"Stress confirmed emotional maturity on both sides.",
            emotional_tone="collaborative"
        ))
    elif "Energy Clash" in title or "Weekend" in title:
        turns.append(StressTurn(
            speaker=ida,
            text=f"Hey, looking at this weekend, I know you were excited about hosting everyone, but my work week has completely drained me. If I don't get quiet downtime, I'm going to be running on empty.",
            thought=f"Setting an energy boundary before resentment builds.",
            emotional_tone="firm"
        ))
        turns.append(StressTurn(
            speaker=idb,
            text=f"I hear you, though I was really looking forward to introducing you to my circle. It's hard not to feel a bit disappointed when plans are already in motion.",
            thought=f"Feeling slightly rejected, but trying not to make it personal.",
            emotional_tone="defensive"
        ))
        turns.append(StressTurn(
            speaker=ida,
            text=f"I know, and I'm really sorry to disappoint. It's truly about my social battery, not about your friends. What if I join for the first hour to say hi, and then head back for a quiet night?",
            thought=f"Offering a compromise that honors both their social pride and my recharge.",
            emotional_tone="empathetic"
        ))
        turns.append(StressTurn(
            speaker=idb,
            text=f"That's a really considerate compromise. Having you there for a bit would mean a lot, and I can stay and catch up with them while you get your rest.",
            thought=f"Relieved {A} offered a workable solution rather than shutting down.",
            emotional_tone="conciliatory"
        ))
        turns.append(StressTurn(
            speaker=ida,
            text=f"Perfect. I love that we can talk about differing energy levels without it turning into an accusation.",
            thought=f"Clear boundaries respected without drama.",
            emotional_tone="collaborative"
        ))
        turns.append(StressTurn(
            speaker=idb,
            text=f"Same here. Knowing you'll tell me what you need instead of faking enthusiasm makes things much easier.",
            thought=f"Authenticity over forced people-pleasing.",
            emotional_tone="collaborative"
        ))
    else:
        turns.append(StressTurn(
            speaker=ida,
            text=f"When misunderstandings happen, I tend to get quiet and take a step back to think before speaking. I want you to know it's not stonewalling—it's how I avoid saying something reactive.",
            thought=f"Explaining emotional regulation style before a real crisis hits.",
            emotional_tone="vulnerable"
        ))
        turns.append(StressTurn(
            speaker=idb,
            text=f"That's good to know, because when someone goes completely silent, my anxiety kicks in and I want to fix things right away. Total silence feels like abandonment.",
            thought=f"Naming the anxious-avoidant friction trigger honestly.",
            emotional_tone="curious"
        ))
        turns.append(StressTurn(
            speaker=ida,
            text=f"I understand why silence feels threatening. Could we agree on a code or quick reassurance—like 'I need twenty minutes to decompress, but I love you and we will resolve this'?",
            thought=f"Offering reassurance anchor to soothe anxiety while keeping boundary.",
            emotional_tone="collaborative"
        ))
        turns.append(StressTurn(
            speaker=idb,
            text=f"A quick reassurance with a specific timeframe would completely disarm my panic. That gives me safety while giving you the space you need.",
            thought=f"Brilliant emotional co-regulation approach.",
            emotional_tone="conciliatory"
        ))
        turns.append(StressTurn(
            speaker=ida,
            text=f"Then that's our agreement. High pressure shouldn't mean guessing what the other is feeling.",
            thought=f"Conflict protocol established smoothly.",
            emotional_tone="firm"
        ))
        turns.append(StressTurn(
            speaker=idb,
            text=f"Agreed. Being able to negotiate our conflict habits like this gives me high confidence in us.",
            thought=f"Resilience score high. Both demonstrated emotional agility.",
            emotional_tone="collaborative"
        ))

    # Resilience scoring based on compatibility baseline and dealbreaker state
    has_db = bool(c.dealbreakers_a or c.dealbreakers_b)
    base_resilience = 7.5 + (0.8 if c.energy_match else -0.4) + (0.5 * len(c.shared_values)) - (2.0 if has_db else 0.0)
    score_a = round(max(3.0, min(9.5, base_resilience + r.uniform(-0.3, 0.4))), 1)
    score_b = round(max(3.0, min(9.5, base_resilience + r.uniform(-0.4, 0.3))), 1)

    verdict_str = "passed" if score_a >= 6.5 else ("conditional" if score_a >= 5.0 else "failed")
    va = StressVerdict(
        agent_for=ida,
        resilience_score=score_a,
        resolution_style="collaborative problem-solving" if score_a >= 6.5 else "cautious boundary negotiation",
        stress_verdict=verdict_str,
        key_takeaway=f"{B} listened without defensiveness and actively negotiated a compromise that respected {A}'s boundaries.",
        growth_potential="High emotional safety; both parties communicate needs transparently under stress."
    )
    vb = StressVerdict(
        agent_for=idb,
        resilience_score=score_b,
        resolution_style="empathetic compromise" if score_b >= 6.5 else "tentative alignment",
        stress_verdict="passed" if score_b >= 6.5 else ("conditional" if score_b >= 5.0 else "failed"),
        key_takeaway=f"{A} was candid about vulnerable constraints rather than withdrawing or people-pleasing.",
        growth_potential="Strong capacity to de-escalate tension and co-regulate emotional pressure."
    )
    return turns, va, vb


# =================================================================== Entry Point

def simulate_first_fight(date: DateRecord, pa: Person, pb: Person) -> FirstFightRecord:
    title, prompt = pick_scenario(pa.analysis, pb.analysis)
    did = date.id
    engine = "offline"

    if config.llm_enabled():
        try:
            turns, va, vb = _simulate_llm(pa, pb, did, title, prompt)
            engine = "claude"
        except Exception:
            turns, va, vb = _simulate_offline(pa, pb, did, title, prompt)
    else:
        turns, va, vb = _simulate_offline(pa, pb, did, title, prompt)

    mutual_resilience = round((va.resilience_score + vb.resilience_score) / 2, 1)

    if mutual_resilience >= 7.0 and va.stress_verdict == "passed" and vb.stress_verdict == "passed":
        outcome = "stronger_together"
    elif mutual_resilience >= 5.0:
        outcome = "navigable_compromise"
    else:
        outcome = "irreconcilable_friction"

    record = FirstFightRecord(
        id=f"ff_{did}",
        date_id=did,
        a=date.a,
        b=date.b,
        scenario_title=title,
        scenario_prompt=prompt,
        turns=turns,
        verdict_a=va,
        verdict_b=vb,
        mutual_resilience=mutual_resilience,
        outcome=outcome,
        engine=engine
    )
    date.first_fight = record
    return record
