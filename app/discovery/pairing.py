"""Find the Instagram account that might belong to a discovered LinkedIn candidate.

Two real sources, both through Apify:
  1. an Instagram handle the LinkedIn result itself mentions (@handle or instagram.com/handle)
  2. otherwise, Google: site:instagram.com "<full name>", first result that is a profile page
The candidate account is then scraped (bio, bio link, private flag) so verification.py can look
for a direct cross-link. A name match alone is never enough to enrol anyone.
"""
from __future__ import annotations

from typing import Optional

from ..scrape import apify
from ..scrape.links import LinkError, normalize_instagram
from .search import provider


class InstagramProfileCandidate:
    def __init__(self, url: str, username: str, bio: str = "", external_url: str = "",
                 is_private: bool = False, location: str = "", found_via: str = ""):
        self.url = url
        self.username = username
        self.bio = bio
        self.external_url = external_url
        self.is_private = is_private
        self.location = location  # Instagram profiles don't expose one; kept for the contradiction check
        self.found_via = found_via


def _handle_from_search(name: str) -> Optional[str]:
    if not name.strip():
        return None
    for r in provider().google_search(f'site:instagram.com "{name}"', limit=5):
        try:
            return normalize_instagram(r["url"])[1]
        except LinkError:
            continue  # posts, reels, tags
    return None


def find_candidate_instagram(linkedin_candidate: dict) -> Optional[InstagramProfileCandidate]:
    """Return the scraped candidate Instagram profile, or None if there is no plausible one."""
    handle, via = linkedin_candidate.get("instagram_hint", "").strip().lower(), "mentioned on LinkedIn"
    try:
        if not handle:
            handle, via = _handle_from_search(linkedin_candidate.get("name", "")), "Google name search"
        if not handle:
            return None
        url, handle = normalize_instagram(f"https://www.instagram.com/{handle}/")
        ig = provider().fetch_instagram(url, handle, posts=1)
    except (apify.ScrapeError, LinkError):
        return None
    return InstagramProfileCandidate(url=url, username=ig.username or handle, bio=ig.bio,
                                     external_url=ig.external_url, is_private=ig.is_private, found_via=via)
