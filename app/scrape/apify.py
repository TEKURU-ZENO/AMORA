"""Scraping the two public sources through Apify actors.

Instagram -> apify/instagram-profile-scraper (public profiles only; private ones are rejected)
LinkedIn  -> a LinkedIn public-profile actor (configurable, default dev_fusion/linkedin-profile-scraper)

Both actors are run with the synchronous `run-sync-get-dataset-items` endpoint and their
output is normalized into our own LinkedInData / InstagramData models, so swapping an actor
only means touching the `_norm_*` functions below.
"""
from __future__ import annotations

import re
from typing import Any

import httpx

from .. import config
from ..models import InstagramData, InstagramPost, LinkedInData, LinkedInExperience

API = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
HASHTAG_RE = re.compile(r"#(\w+)")


class ScrapeError(RuntimeError):
    pass


class PrivateProfile(ScrapeError):
    pass


def _run_actor(actor: str, payload: dict) -> list[dict]:
    token = config.apify_token()
    if not token:
        raise ScrapeError("APIFY_TOKEN is not set on the server, live scraping is disabled")
    r = httpx.post(
        API.format(actor=actor),
        params={"token": token, "timeout": config.APIFY_TIMEOUT_S},
        json=payload,
        timeout=config.APIFY_TIMEOUT_S + 30,
    )
    if r.status_code >= 400:
        raise ScrapeError(f"Apify actor {actor} failed ({r.status_code}): {r.text[:300]}")
    items = r.json()
    if not isinstance(items, list) or not items:
        raise ScrapeError(f"Apify actor {actor} returned no data")
    return items


def _first(d: dict, *keys, default=None):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", [], {}):
            return v
    return default


# ---------------- Instagram ----------------

def _norm_instagram(url: str, raw: dict) -> InstagramData:
    posts = []
    for p in (_first(raw, "latestPosts", "posts", default=[]) or [])[:24]:
        cap = p.get("caption") or ""
        tags = p.get("hashtags") or HASHTAG_RE.findall(cap)
        posts.append(InstagramPost(
            caption=cap[:600],
            hashtags=[t.lower() for t in tags][:20],
            location=p.get("locationName") or "",
            kind=(p.get("type") or "image").lower(),
        ))
    return InstagramData(
        url=url,
        username=_first(raw, "username", default=""),
        full_name=_first(raw, "fullName", "full_name", default=""),
        bio=_first(raw, "biography", "bio", default=""),
        is_private=bool(_first(raw, "private", "isPrivate", default=False)),
        external_url=_first(raw, "externalUrl", "external_url", default="") or next(
            (x.get("url") for x in raw.get("externalUrls") or [] if isinstance(x, dict) and x.get("url")), ""),
        followers=int(_first(raw, "followersCount", "followers", default=0) or 0),
        following=int(_first(raw, "followsCount", "following", default=0) or 0),
        posts=posts,
    )


def fetch_instagram(url: str, username: str, posts: int = 24) -> InstagramData:
    """Scrape a profile and report what is there, private or not (discovery needs to know)."""
    items = _run_actor(config.APIFY_INSTAGRAM_ACTOR, {"usernames": [username], "resultsLimit": posts})
    return _norm_instagram(url, items[0])


def scrape_instagram(url: str, username: str) -> InstagramData:
    data = fetch_instagram(url, username)
    if data.is_private:
        raise PrivateProfile("This Instagram is private. Only public profiles can be read.")
    return data


# ---------------- LinkedIn ----------------

def _norm_linkedin(url: str, raw: dict) -> LinkedInData:
    exps = []
    for e in (_first(raw, "experiences", "experience", "positions", default=[]) or [])[:10]:
        desc = e.get("description") or ""
        if not desc and isinstance(e.get("subComponents"), list):
            bits = []
            for sc in e["subComponents"]:
                for d in sc.get("description", []) or []:
                    if isinstance(d, dict) and d.get("text"):
                        bits.append(d["text"])
            desc = " ".join(bits)
        exps.append(LinkedInExperience(
            title=_first(e, "title", "position", default=""),
            company=_first(e, "subtitle", "companyName", "company", default=""),
            duration=_first(e, "caption", "duration", "dateRange", default=""),
            description=str(desc)[:800],
        ))

    def titles(key_opts):
        out = []
        for x in (_first(raw, *key_opts, default=[]) or []):
            out.append(x.get("title") or x.get("name") or x.get("schoolName") or "" if isinstance(x, dict) else str(x))
        return [o for o in out if o][:20]

    return LinkedInData(
        url=url,
        full_name=_first(raw, "fullName", "full_name", "name", default="")
        or f"{raw.get('firstName', '')} {raw.get('lastName', '')}".strip(),
        headline=_first(raw, "headline", "jobTitle", default=""),
        about=_first(raw, "about", "summary", default=""),
        location=_first(raw, "addressWithCountry", "location", "geoLocationName", default=""),
        experience=exps,
        education=titles(["educations", "education"]),
        skills=titles(["skills"]),
        volunteering=titles(["volunteerAndAwards", "volunteering", "volunteerExperiences"]),
        languages=titles(["languages"]),
    )


def scrape_linkedin(url: str) -> LinkedInData:
    items = _run_actor(config.APIFY_LINKEDIN_ACTOR, {"profileUrls": [url]})
    return _norm_linkedin(url, items[0])


# ---------------- Search (discovery) ----------------

def google_search(query: str, limit: int = 10) -> list[dict]:
    """Organic Google results via Apify: [{title, url, description}, ...]."""
    items = _run_actor(config.APIFY_SEARCH_ACTOR, {
        "queries": query, "maxPagesPerQuery": 1, "resultsPerPage": max(10, limit),
        "mobileResults": False, "saveHtml": False,
    })
    out = []
    for page in items:
        for r in page.get("organicResults") or []:
            if r.get("url"):
                out.append({"title": r.get("title") or "", "url": r["url"], "description": r.get("description") or ""})
    return out
