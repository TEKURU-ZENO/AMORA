"""Second-Date Planner and Human Intro Drafter.

Turns dating agents from talkers into doers:
1. When two agents agree to a second date, they negotiate an actionable, specific plan:
   venue, activity, time slot, budget tier, and dress code/vibe.
2. Drafts a high-converting, personalized first direct message (DM) for the human
   to copy and send to their match on Instagram or LinkedIn, referencing specific highlights
   and banter from the date.
"""
from __future__ import annotations

import hashlib
import random
from pydantic import BaseModel, Field

from .. import config
from ..models import Analysis, DateRecord, Person, SecondDatePlan
from . import llm
from .compat import compute


def first(a: Analysis) -> str:
    return a.display_name.split()[0]


class PlanNegotiationOutput(BaseModel):
    activity: str = Field(description="Specific 2nd date activity tailored to their shared interests")
    venue_name: str = Field(description="Specific venue name or venue concept")
    location_idea: str = Field(description="Neighborhood or setting")
    day_and_time: str = Field(description="e.g. Saturday afternoon at 2:00 PM, Thursday evening at 7:30 PM")
    budget_tier: str = Field(description="$, $$, or $$$")
    vibe: str = Field(description="e.g. Cozy coffee & vinyl, High-energy bouldering, Candlelit jazz")
    plan_notes: str = Field(description="Why this plan works well for both personalities")
    drafted_intro_for_a: str = Field(description="Ready-to-send DM from human A to human B, witty and referencing date banter")
    drafted_intro_for_b: str = Field(description="Ready-to-send DM from human B to human A, warm and referencing date banter")


def _plan_llm(date: DateRecord, pa: Person, pb: Person) -> SecondDatePlan:
    a, b = pa.analysis, pb.analysis
    fa, fb = first(a), first(b)
    transcript_summary = "\n".join(f"{t.speaker}: {t.text}" for t in date.turns[:6])

    sys_prompt = (
        f"You are the executive date concierge and wing-agent for {a.display_name} and {b.display_name}. "
        f"Both agents went on a first date at {date.venue} and agreed to a second date! "
        f"Negotiate an actionable second date plan based on their briefs and draft ready-to-send first DMs for the humans."
    )
    user_prompt = (
        f"{fa}'s Brief: Hobbies {a.hobbies}, Interests {a.interests}, Ideal Date: {a.ideal_date}, Style: {a.communication_style}\n"
        f"{fb}'s Brief: Hobbies {b.hobbies}, Interests {b.interests}, Ideal Date: {b.ideal_date}, Style: {b.communication_style}\n"
        f"Highlights from date at {date.venue}:\n{transcript_summary}\n\n"
        f"Produce a realistic plan and personalized ready-to-send DM for each human."
    )
    out = llm.structured(sys_prompt, user_prompt, PlanNegotiationOutput, max_tokens=650)
    return SecondDatePlan(
        id=f"plan_{date.id}",
        date_id=date.id,
        activity=out.activity,
        venue_name=out.venue_name,
        location_idea=out.location_idea,
        day_and_time=out.day_and_time,
        budget_tier=out.budget_tier,
        vibe=out.vibe,
        plan_notes=out.plan_notes,
        drafted_intro_for_a=out.drafted_intro_for_a,
        drafted_intro_for_b=out.drafted_intro_for_b,
        agreed=True
    )


def _plan_offline(date: DateRecord, pa: Person, pb: Person) -> SecondDatePlan:
    a, b = pa.analysis, pb.analysis
    fa, fb = first(a), first(b)
    c = compute(a, b)
    shared = c.shared_hobbies + c.shared_interests + a.hobbies + b.hobbies
    top_hobby = shared[0].lower() if shared else "exploring local spots"

    seed = int(hashlib.sha1(f"plan|{min(date.a, date.b)}|{max(date.a, date.b)}".encode()).hexdigest()[:8], 16)
    r = random.Random(seed)

    activities = [
        (f"Weekend morning {top_hobby} followed by artisan pastry & coffee", "Little Owl Café & Roastery", "Saturday at 10:30 AM", "$", "Cozy & Active"),
        (f"Hidden vinyl listening lounge & craft cocktails", "The Velvet Groove Speakeasy", "Friday at 8:00 PM", "$$", "Intimate & Atmospheric"),
        (f"Interactive pottery workshop and gallery stroll", "Clay & Canvas Studio", "Sunday at 2:00 PM", "$$", "Playful & Creative"),
        (f"Twilight food truck night market & rooftop stargazing", "Bayside Night Market", "Thursday at 7:00 PM", "$", "Lively & Low-Pressure"),
    ]
    activity, venue, day_time, budget, vibe = r.choice(activities)

    # Tailored DM draft for human A to copy & send to human B
    dm_a = (
        f"Hey {fb}! Our agents went on a date and apparently decided we're a match. "
        f"Mine mentioned you're into {top_hobby}—I'm holding them to the plan they made for {venue} this {day_time.split()[0]}. "
        f"Coffee on me if our agents were actually right?"
    )

    # Tailored DM draft for human B to copy & send to human A
    dm_b = (
        f"Hi {fa}! Fair warning: my agent gave our date a glowing review and swore we need to do {activity.lower()}. "
        f"Are you free this {day_time.split()[0]} to see if real life beats agent simulations?"
    )

    notes = (
        f"Grounded in mutual enthusiasm for {top_hobby}. "
        f"Balances {fa}'s {a.communication_style.lower()} energy with {fb}'s preference for {b.ideal_date.lower()}."
    )

    return SecondDatePlan(
        id=f"plan_{date.id}",
        date_id=date.id,
        activity=activity,
        venue_name=venue,
        location_idea="Downtown Arts District",
        day_and_time=day_time,
        budget_tier=budget,
        vibe=vibe,
        plan_notes=notes,
        drafted_intro_for_a=dm_a,
        drafted_intro_for_b=dm_b,
        agreed=True
    )


def plan_second_date(date: DateRecord, pa: Person, pb: Person) -> SecondDatePlan:
    if config.llm_enabled():
        try:
            plan = _plan_llm(date, pa, pb)
        except Exception:
            plan = _plan_offline(date, pa, pb)
    else:
        plan = _plan_offline(date, pa, pb)

    date.second_date_plan = plan
    return plan
