"""The demo personas, re-addressed as real-shaped profile URLs so tests can push them through
the production ingest() path (link validation + stubbed Apify scrapes)."""
from scripts.synthetic import build as _build


def build():
    out = []
    for handle, li, ig in _build():
        li = li.model_copy(update={"url": f"https://www.linkedin.com/in/{handle}/"})
        ig = ig.model_copy(update={"url": f"https://www.instagram.com/{ig.username}/"})
        out.append((handle, li, ig))
    return out
