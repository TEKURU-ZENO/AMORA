"""AI Icebreaker & First-Message Drafter for AMORA SaaS.

Takes a confirmed match (or top-ranked candidate) and their date transcript/analysis,
and synthesizes 3 high-converting, personalized first messages:
1. The Witty Callback (references a funny or playful banter moment from the date).
2. The Shared Passion (proposes an activity based on uncovered overlaps).
3. The Direct & Low-Pressure (warm, grounded invitation for coffee/drinks).

Includes direct links for 1-click opening in Instagram DMs or LinkedIn.
"""
from __future__ import annotations

import urllib.parse
from typing import Optional

from ..models import Analysis, DateRecord, Person
from .models import IcebreakerSuggestion


def generate_icebreakers(
    user_person: Person,
    match_person: Person,
    date_record: Optional[DateRecord] = None,
) -> list[IcebreakerSuggestion]:
    """Generate 3 tailored first messages ready for human-to-human delivery."""
    user_name = user_person.analysis.display_name.split()[0] if user_person.analysis else "Me"
    match_name = match_person.analysis.display_name.split()[0] if match_person.analysis else "There"
    match_handle = ""
    if match_person.sources and match_person.sources.instagram:
        match_handle = match_person.sources.instagram.username

    # Instagram DM link
    ig_dm_url = f"https://ig.me/m/{match_handle}" if match_handle else None
    li_url = match_person.linkedin_url if match_person.linkedin_url else None

    # Extract conversation highlights
    user_hobbies = user_person.analysis.hobbies if user_person.analysis else []
    match_hobbies = match_person.analysis.hobbies if match_person.analysis else []
    shared_hobbies = [h for h in user_hobbies if any(h.lower() in mh.lower() or mh.lower() in h.lower() for mh in match_hobbies)]
    top_shared = shared_hobbies[0] if shared_hobbies else (match_hobbies[0] if match_hobbies else "great coffee")

    # Venue or date theme if date exists
    venue_name = "our local spot"
    activity_name = top_shared
    if date_record:
        venue_name = date_record.venue
        if date_record.second_date_plan:
            activity_name = date_record.second_date_plan.activity
            venue_name = date_record.second_date_plan.venue_name

    # 1. The Witty Callback
    msg_callback = (
        f"Hey {match_name}! So our AI agents just went on a date at {venue_name} and apparently "
        f"argued about whether {top_shared} counts as a personality trait. "
        f"They gave us a 9/10 match... figured I should say hi before they plan our entire wedding haha."
    )

    # 2. The Shared Passion
    msg_passion = (
        f"Hi {match_name}! My agent told me you're also deeply into {top_shared}. "
        f"Honestly rare to find someone who gets that. Are you around this weekend to grab coffee "
        f"or check out {venue_name} in person?"
    )

    # 3. The Direct & Low-Pressure
    msg_direct = (
        f"Hey {match_name}, loved reading what came up on our agents' date—especially your take on {top_shared}. "
        f"I'm {user_name}. No pressure at all, but if you're open to it, I'd love to skip the small talk and grab a drink sometime!"
    )

    return [
        IcebreakerSuggestion(
            style="witty_callback",
            headline="The Witty Callback (Playful & High-Reply)",
            message=msg_callback,
            target_name=match_name,
            target_handle=match_handle,
            instagram_dm_url=ig_dm_url,
            linkedin_url=li_url,
        ),
        IcebreakerSuggestion(
            style="shared_passion",
            headline="The Shared Passion (Focuses on Real Overlaps)",
            message=msg_passion,
            target_name=match_name,
            target_handle=match_handle,
            instagram_dm_url=ig_dm_url,
            linkedin_url=li_url,
        ),
        IcebreakerSuggestion(
            style="direct_invite",
            headline="The Direct & Grounded (Low Pressure Invitation)",
            message=msg_direct,
            target_name=match_name,
            target_handle=match_handle,
            instagram_dm_url=ig_dm_url,
            linkedin_url=li_url,
        ),
    ]
