"""Fictional discovery provider for demo mode (AGENTDATE_DEMO=1).

Shaped exactly like the Apify Google-search and Instagram results the live provider gets, so the
real verification rules run on it and every outcome shows up: direct cross-link, handle mentioned
on LinkedIn, ambiguous (human review), private, and no Instagram at all. Every person, company and
handle is invented; handles end in "-demo" / ".demo" so they can't be mistaken for real accounts.
"""
from __future__ import annotations

from ..models import InstagramData

LINKEDIN_RESULTS = [
    {"title": "Maya Patel - Lead Product Designer - Imaginary Studio | LinkedIn",
     "url": "https://www.linkedin.com/in/maya-patel-demo", "description": "Location: Bengaluru · Ceramics and trail running."},
    {"title": "Liam Chen - Robotics Engineer - Mock Systems | LinkedIn",
     "url": "https://www.linkedin.com/in/liam-chen-demo", "description": "Location: Pune · Bouldering on weekends, @liam_chen.demo"},
    {"title": "Elena Rostova - Research Scientist - Fictive Labs | LinkedIn",
     "url": "https://www.linkedin.com/in/elena-rostova-demo", "description": "Location: Mumbai · NLP and classical piano."},
    {"title": "Zoe Alvarez - Climate Policy Fellow - Hypothetical Capital | LinkedIn",
     "url": "https://www.linkedin.com/in/zoe-alvarez-demo", "description": "Location: Delhi · Marathoner."},
    {"title": "Aravind Nair - Fintech Strategy - Notreal.ai | LinkedIn",
     "url": "https://www.linkedin.com/in/aravind-nair-demo", "description": "Location: Chennai · Specialty coffee."},
    {"title": "Omar Haddad - Chef - Sample & Co | LinkedIn",
     "url": "https://www.linkedin.com/in/omar-haddad-demo", "description": "Location: Hyderabad · Restaurants."},
]

INSTAGRAM_BY_NAME = {"Maya Patel": "maya.patel.demo", "Elena Rostova": "elena.rostova.demo",
                     "Zoe Alvarez": "zoe.alvarez.demo", "Aravind Nair": "aravind.nair.demo"}

INSTAGRAM = {
    "maya.patel.demo": InstagramData(url="", username="maya.patel.demo", bio="designing things ✦ trails & pottery",
                                     external_url="https://www.linkedin.com/in/maya-patel-demo"),
    "liam_chen.demo": InstagramData(url="", username="liam_chen.demo",
                                    bio="robotics & bouldering · linkedin.com/in/liam-chen-demo"),
    "elena.rostova.demo": InstagramData(url="", username="elena.rostova.demo", bio="Classical piano. Coffee and sonatas."),
    "zoe.alvarez.demo": InstagramData(url="", username="zoe.alvarez.demo", is_private=True),
    "aravind.nair.demo": InstagramData(url="", username="aravind.nair.demo",
                                       bio="coffee & fintech · linkedin.com/in/aravind-nair-demo"),
}


def google_search(query: str, limit: int = 10) -> list[dict]:
    if query.startswith("site:linkedin.com/in/"):
        terms = [t for t in query.removeprefix("site:linkedin.com/in/").lower().split() if t]
        hits = [r for r in LINKEDIN_RESULTS if any(t in (r["title"] + r["description"]).lower() for t in terms)]
        return (hits or LINKEDIN_RESULTS)[:limit]
    for name, handle in INSTAGRAM_BY_NAME.items():
        if f'"{name}"' in query:
            return [{"title": name, "url": f"https://www.instagram.com/{handle}/", "description": ""}]
    return []


def fetch_instagram(url: str, username: str, posts: int = 24) -> InstagramData:
    from ..scrape.apify import ScrapeError
    if username not in INSTAGRAM:
        raise ScrapeError(f"Demo provider has no account @{username}")
    return INSTAGRAM[username].model_copy(update={"url": url})
