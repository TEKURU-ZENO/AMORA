"""Find candidate LinkedIn profiles on the public web, through Apify's Google Search actor.

There is no offline or mock provider: every candidate is a real public LinkedIn page that
Google returned for the query. Without APIFY_TOKEN, discovery refuses to run.
"""
from __future__ import annotations

import re

from .. import config
from ..scrape import apify
from ..scrape.links import LinkError, normalize_linkedin

# "@handle" or "instagram.com/handle" mentioned in a title or snippet
IG_MENTION_RE = re.compile(r"(?:instagram\.com/|(?<![\w.])@)([A-Za-z0-9._]{2,30})")
LOCATION_RE = re.compile(r"Location:\s*([^·|\n]+)")
TITLE_SPLIT_RE = re.compile(r"\s+[-–|]\s+")


class DiscoveryUnavailable(RuntimeError):
    pass


def _parse_result(r: dict) -> dict | None:
    try:
        url, handle = normalize_linkedin(r["url"])
    except LinkError:
        return None  # company pages, posts, directory pages
    parts = TITLE_SPLIT_RE.split(r.get("title", "").replace(" | LinkedIn", "").replace(" - LinkedIn", ""))
    name = parts[0].strip() or handle
    desc = r.get("description", "")
    headline = " · ".join(p.strip() for p in parts[1:] if p.strip()) or desc[:160]
    loc = LOCATION_RE.search(desc)
    mention = IG_MENTION_RE.search(f"{r.get('title', '')} {desc}")
    return {"url": url, "handle": handle, "name": name, "headline": headline, "snippet": desc,
            "location": loc.group(1).strip() if loc else "",
            "instagram_hint": mention.group(1).lower() if mention else ""}


def search_linkedin(query: str, limit: int = 10) -> list[dict]:
    if not config.scraping_enabled():
        raise DiscoveryUnavailable("Discovery searches the web through Apify, and no APIFY_TOKEN is set on this server.")
    results = apify.google_search(f"site:linkedin.com/in/ {query}".strip(), limit=limit * 2)
    seen, out = set(), []
    for r in results:
        c = _parse_result(r)
        if c and c["handle"] not in seen:
            seen.add(c["handle"])
            out.append(c)
        if len(out) >= limit:
            break
    return out
