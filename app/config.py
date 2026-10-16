import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
DB_PATH = DATA_DIR / "agentdate.sqlite3"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("AGENTDATE_MODEL", "claude-sonnet-4-5")

APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")
# Actor IDs are configurable because Apify marketplace actors change over time.
APIFY_INSTAGRAM_ACTOR = os.getenv("APIFY_INSTAGRAM_ACTOR", "apify~instagram-profile-scraper")
APIFY_LINKEDIN_ACTOR = os.getenv("APIFY_LINKEDIN_ACTOR", "dev_fusion~linkedin-profile-scraper")
APIFY_TIMEOUT_S = int(os.getenv("APIFY_TIMEOUT_S", "180"))

# Dating harness knobs
SHORTLIST_K = int(os.getenv("SHORTLIST_K", "6"))       # each agent asks out its top-K after screening
DATE_TURNS = int(os.getenv("DATE_TURNS", "10"))         # messages per date (both sides combined)
MAX_PARALLEL_DATES = int(os.getenv("MAX_PARALLEL_DATES", "6"))


def llm_enabled() -> bool:
    return bool(ANTHROPIC_API_KEY)


def scraping_enabled() -> bool:
    return bool(APIFY_TOKEN)
