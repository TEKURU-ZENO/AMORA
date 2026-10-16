import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Read KEY=VALUE lines from a local .env (gitignored). Real environment variables win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv(ROOT / ".env")
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
DB_PATH = DATA_DIR / "agentdate.sqlite3"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("AGENTDATE_MODEL", "claude-sonnet-4-5")

APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")
# Actor IDs are configurable because Apify marketplace actors change over time.
APIFY_INSTAGRAM_ACTOR = os.getenv("APIFY_INSTAGRAM_ACTOR", "apify~instagram-profile-scraper")
APIFY_LINKEDIN_ACTOR = os.getenv("APIFY_LINKEDIN_ACTOR", "dev_fusion~linkedin-profile-scraper")
# Discovery searches Google through Apify for public LinkedIn / Instagram profile pages.
APIFY_SEARCH_ACTOR = os.getenv("APIFY_SEARCH_ACTOR", "apify~google-search-scraper")
APIFY_TIMEOUT_S = int(os.getenv("APIFY_TIMEOUT_S", "180"))

# Dating harness knobs
SHORTLIST_K = int(os.getenv("SHORTLIST_K", "6"))       # each agent asks out its top-K after screening
DATE_TURNS = int(os.getenv("DATE_TURNS", "10"))         # messages per date (both sides combined)
MAX_PARALLEL_DATES = int(os.getenv("MAX_PARALLEL_DATES", "6"))

# Access & Privacy
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", os.getenv("AGENTDATE_DEMO_KEY", "agentdate-demo-secret"))


def llm_enabled() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def apify_token() -> str:
    """Read live, so tests and a reloaded .env see the same value the scrapers use."""
    return os.getenv("APIFY_TOKEN", "")


def scraping_enabled() -> bool:
    return bool(apify_token())


