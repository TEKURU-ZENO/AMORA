"""Shared test setup. Runs before any test module imports the app.

The app is Apify-only, so tests stub Apify itself: scrape_linkedin / fetch_instagram /
google_search answer from fixtures, and any other call to the real API fails the test
instead of spending credits. A local .env never leaks in, because every key is set here.
"""
import os
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp()
os.environ["APIFY_TOKEN"] = "test-token"  # never a real token; nothing below reaches Apify
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["ADMIN_API_KEY"] = "test-secret-key-123"

from app import config  # noqa: E402
from app.models import InstagramData  # noqa: E402
from app.scrape import apify  # noqa: E402
from tests.personas import build  # noqa: E402

config.ADMIN_API_KEY = "test-secret-key-123"

PERSONAS = build()
LINKEDIN = {li.url: li for _, li, _ in PERSONAS}
INSTAGRAM = {ig.username: ig for _, _, ig in PERSONAS}

# Discovery fixtures, shaped like Apify google-search-scraper organic results.
LI_RESULTS = [
    {"title": "Maya Patel - Lead Product Designer - Stripe | LinkedIn", "url": "https://www.linkedin.com/in/maya-patel-design",
     "description": "Location: San Francisco · Ceramicist and trail runner."},
    {"title": "Liam Chen - Robotics Engineer | LinkedIn", "url": "https://www.linkedin.com/in/liam-chen-robotics",
     "description": "Location: Seattle · Bouldering on weekends, @liam_chen_climbs"},
    {"title": "Elena Rostova - Research Scientist | LinkedIn", "url": "https://www.linkedin.com/in/elena-rostova-ai",
     "description": "Location: London · NLP and classical piano."},
    {"title": "Zoe Alvarez - Climate Policy Fellow | LinkedIn", "url": "https://www.linkedin.com/in/zoe-alvarez-climate",
     "description": "Location: New York · Marathoner."},
    {"title": "Omar Haddad - Chef | LinkedIn", "url": "https://www.linkedin.com/in/omar-haddad-chef",
     "description": "Location: Dubai · Restaurants."},
    {"title": "Acme Corp | LinkedIn", "url": "https://www.linkedin.com/company/acme", "description": "Company page"},
]
IG_BY_NAME = {"Maya Patel": "maya.patel.design", "Elena Rostova": "elena_piano_notes", "Zoe Alvarez": "zoe_alvarez_runs"}
DISCOVERY_IG = {
    "maya.patel.design": InstagramData(url="", username="maya.patel.design", bio="designing at stripe ✦ trails & pottery",
                                       external_url="https://www.linkedin.com/in/maya-patel-design"),
    "liam_chen_climbs": InstagramData(url="", username="liam_chen_climbs",
                                      bio="robotics & bouldering. linkedin.com/in/liam-chen-robotics"),
    "elena_piano_notes": InstagramData(url="", username="elena_piano_notes", bio="Classical pianist in London."),
    "zoe_alvarez_runs": InstagramData(url="", username="zoe_alvarez_runs", is_private=True),
}
CALLS: list[tuple[str, str]] = []


def _no_network(actor, payload):
    raise AssertionError(f"Test tried to call the real Apify API ({actor}). Stub it in conftest.py.")


def _scrape_linkedin(url):
    CALLS.append(("linkedin", url))
    if url not in LINKEDIN:
        raise apify.ScrapeError(f"Apify actor returned no data for {url}")
    return LINKEDIN[url]


def _fetch_instagram(url, username, posts=24):
    CALLS.append(("instagram", username))
    data = INSTAGRAM.get(username) or DISCOVERY_IG.get(username)
    if not data:
        raise apify.ScrapeError(f"Apify actor returned no data for @{username}")
    return data.model_copy(update={"url": url})


def _google_search(query, limit=10):
    CALLS.append(("search", query))
    if query.startswith("site:linkedin.com/in/"):
        return LI_RESULTS
    for name, handle in IG_BY_NAME.items():
        if f'"{name}"' in query:
            return [{"title": "post", "url": f"https://www.instagram.com/p/{handle}x/", "description": ""},
                    {"title": name, "url": f"https://www.instagram.com/{handle}/", "description": ""}]
    return []


apify._run_actor = _no_network
apify.scrape_linkedin = _scrape_linkedin
apify.fetch_instagram = _fetch_instagram
apify.google_search = _google_search


def seed_pool(n: int = 25) -> list:
    """Fill the pool the way production does: ingest() from two links, scraped via (stubbed) Apify."""
    from app import harness
    return [harness.ingest(li.url, ig.url, True, progress=lambda m: None) for _, li, ig in PERSONAS[:n]]
