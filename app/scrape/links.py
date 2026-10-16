"""Validation of the two official links. We accept only these two sources."""
from __future__ import annotations

import re
from urllib.parse import urlparse

LI_RE = re.compile(r"^/in/([A-Za-z0-9\-_%]{3,100})/?$")
IG_RE = re.compile(r"^/([A-Za-z0-9._]{1,30})/?$")
IG_RESERVED = {"p", "reel", "reels", "explore", "stories", "accounts", "direct", "tv"}


class LinkError(ValueError):
    pass


def normalize_linkedin(url: str) -> tuple[str, str]:
    u = urlparse(url.strip())
    host = (u.netloc or "").lower().removeprefix("www.")
    if not host.endswith("linkedin.com"):
        raise LinkError("LinkedIn link must be a linkedin.com/in/<handle> profile URL")
    m = LI_RE.match(u.path)
    if not m:
        raise LinkError("LinkedIn link must point to a personal profile (linkedin.com/in/<handle>)")
    handle = m.group(1)
    return f"https://www.linkedin.com/in/{handle}/", handle.lower()


def normalize_instagram(url: str) -> tuple[str, str]:
    u = urlparse(url.strip())
    host = (u.netloc or "").lower().removeprefix("www.")
    if host not in {"instagram.com", "instagr.am"}:
        raise LinkError("Instagram link must be an instagram.com/<username> profile URL")
    m = IG_RE.match(u.path)
    if not m or m.group(1).lower() in IG_RESERVED:
        raise LinkError("Instagram link must point to a profile (instagram.com/<username>), not a post")
    handle = m.group(1)
    return f"https://www.instagram.com/{handle}/", handle.lower()


def person_id(li_handle: str, ig_handle: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", li_handle).strip("-")[:40]
    return slug or ig_handle
