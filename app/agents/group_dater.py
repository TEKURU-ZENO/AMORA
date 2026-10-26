"""Multi-Stage Dating and Group Hangout Engine.

Extends dating into realistic multi-stage progression:
1. Speed Date: Rapid 4-turn screening round.
2. Deep Dinner: Comprehensive 10-turn intimate date.
3. Group Hangout: 3 or 4 agents go on a group outing together (Pub Trivia, Escape Room, Gallery Walk),
   observing how their matches navigate social dynamics, group banter, inclusivity, and warmth.
"""
from __future__ import annotations

import hashlib
import random
from typing import Optional
from pydantic import BaseModel, Field

from .. import config
from ..models import Analysis, GroupDateRecord, GroupTurn, Person
from . import llm


def first(a: Analysis) -> str:
    return a.display_name.split()[0]


GROUP_ACTIVITIES = [
    ("Pub Trivia Night & Craft Brews", "The Black Dog Taphouse", "competitive banter, pop culture knowledge, and team collaboration"),
    ("Sci-Fi Escape Room Challenge", "Paradox Mystery Labs", "problem-solving under pressure, listening to others, and sharing clues"),
    ("Modern Art Gallery Crawl & Wine Tasting", "Lumina Contemporary Arts", "creative interpretations, aesthetic opinions, and relaxed mingling"),
    ("Sunset Beach Bonfire & Acoustic Jam", "Ocean View Cove", "storytelling, warmth, group laughter, and casual vulnerability"),
]


class LLMGroupTurn(BaseModel):
    speaker: str
    target: Optional[str] = None
    say: str
    thought: str = ""


class LLMGroupOutput(BaseModel):
    group_chemistry: float = Field(ge=0, le=10)
    turns: list[LLMGroupTurn]
    social_observations: dict[str, list[str]] = Field(default_factory=dict)
    takeaways: list[str] = Field(default_factory=list)


def _group_hangout_llm(people: list[Person], activity: str, venue: str) -> GroupDateRecord:
    roster = ", ".join(p.analysis.display_name for p in people if p.analysis)
    sys_prompt = (
        f"You are the group interaction simulator for AMORA. "
        f"Participants: {roster}. "
        f"Activity: {activity} at {venue}. "
        f"Simulate 8 realistic group turns where participants interact with each other, joke, "
        f"react to the group challenge, and demonstrate their social dynamics."
    )
    user_prompt = "Generate the group hangout conversation and evaluate social dynamics."
    out = llm.structured(sys_prompt, user_prompt, LLMGroupOutput, max_tokens=900)
    turns = [
        GroupTurn(speaker=t.speaker, text=t.say, thought=t.thought, target=t.target)
        for t in out.turns
    ]
    pids = [p.id for p in people]
    gdid = hashlib.sha1("-".join(sorted(pids)).encode()).hexdigest()[:10]
    return GroupDateRecord(
        id=f"grp_{gdid}",
        participants=pids,
        activity=activity,
        venue=venue,
        turns=turns,
        group_chemistry=round(out.group_chemistry, 1),
        social_observations=out.social_observations,
        takeaways=out.takeaways,
        engine="claude"
    )


def _group_hangout_offline(people: list[Person], activity: str, venue: str) -> GroupDateRecord:
    pids = [p.id for p in people]
    gdid = hashlib.sha1("-".join(sorted(pids)).encode()).hexdigest()[:10]
    names = [first(p.analysis) if p.analysis else p.id for p in people]
    by_pid = {p.id: p for p in people}

    seed = int(hashlib.sha1(f"group|{gdid}".encode()).hexdigest()[:8], 16)
    r = random.Random(seed)

    turns: list[GroupTurn] = []

    # Turn 1: Icebreaker by first person
    p0, n0 = people[0], names[0]
    turns.append(GroupTurn(
        speaker=p0.id,
        text=f"Alright everyone, welcome to {venue}! If we're doing {activity.lower()}, I propose we make a pact to win this or go down together in flames.",
        thought="Kicking off with inclusive, playful energy."
    ))

    # Turn 2: Second person chimes in
    p1, n1 = people[1], names[1]
    turns.append(GroupTurn(
        speaker=p1.id,
        target=p0.id,
        text=f"Haha, I like the optimism {n0}! Just warning you all, my useless trivia knowledge on random 90s music is surprisingly dangerous.",
        thought="Bouncing off the group leader's energy."
    ))

    # Turn 3: Third person
    p2, n2 = people[2], names[2]
    turns.append(GroupTurn(
        speaker=p2.id,
        text=f"Count me in. I'll handle history and obscure geography questions. What's our team name going to be?",
        thought="Contributing a concrete strength to the group dynamic."
    ))

    # Turn 4: Fourth person (or p0 if 3 people)
    p3, n3 = (people[3], names[3]) if len(people) > 3 else (people[0], names[0])
    turns.append(GroupTurn(
        speaker=p3.id,
        text=f"How about 'The Algorithm Made Us Do It'? I brought good luck energy and snacks.",
        thought="Offering lighthearted humor to break remaining ice."
    ))

    # Mid-event banter
    turns.append(GroupTurn(
        speaker=p1.id,
        target=p2.id,
        text=f"Wait {n2}, your call on that last question was brilliant. We would have completely missed that clue.",
        thought="Validating teammate and building group chemistry."
    ))
    turns.append(GroupTurn(
        speaker=p2.id,
        text=f"Teamwork! Honestly, {n0}'s quick thinking under time pressure saved us there.",
        thought="Passing credit back to the group."
    ))
    turns.append(GroupTurn(
        speaker=p0.id,
        text=f"Whatever the final score is, this was genuinely way more fun than I expected. Drinks on me for round two?",
        thought="Extending the social momentum."
    ))
    turns.append(GroupTurn(
        speaker=p3.id,
        text=f"Definitely yes. It's rare for four people meeting for the first time to click this naturally.",
        thought="Confirming strong group harmony."
    ))

    social_observations: dict[str, list[str]] = {}
    for i, p in enumerate(people):
        n = names[i]
        if i == 0:
            social_observations[p.id] = [f"{n} naturally assumed an inclusive facilitator role", "Kept energy upbeat and welcoming for everyone"]
        elif i == 1:
            social_observations[p.id] = [f"{n} brought witty banter and playful competitive spirit", "Attentive listener who validated others' ideas"]
        elif i == 2:
            social_observations[p.id] = [f"{n} demonstrated collaborative teamwork and calm problem-solving", "Comfortable sharing the spotlight"]
        else:
            social_observations[p.id] = [f"{n} contributed humor and high social adaptability", "Warm group contributor"]

    takeaways = [
        f"High group synergy observed at {venue}; all {len(people)} participants contributed equitably.",
        "Social dynamics revealed natural warmth, absence of conversational dominance, and high mutual respect.",
        "Cross-dating signals indicate strong organic compatibility beyond 1-on-1 environments."
    ]

    return GroupDateRecord(
        id=f"grp_{gdid}",
        participants=pids,
        activity=activity,
        venue=venue,
        turns=turns,
        group_chemistry=8.6,
        social_observations=social_observations,
        takeaways=takeaways,
        engine="offline"
    )


def run_group_hangout(people: list[Person]) -> GroupDateRecord:
    if len(people) < 3:
        raise ValueError("Group hangout requires at least 3 participants.")
    # Pick activity
    act, venue, _ = random.choice(GROUP_ACTIVITIES)
    if config.llm_enabled():
        try:
            return _group_hangout_llm(people, act, venue)
        except Exception:
            return _group_hangout_offline(people, act, venue)
    return _group_hangout_offline(people, act, venue)
