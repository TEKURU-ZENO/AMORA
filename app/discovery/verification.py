from __future__ import annotations

import re
from typing import Optional, Tuple
from .pairing import InstagramProfileCandidate


def _extract_cities(loc: str) -> set[str]:
    """Tokenize location string into lowercased city/state keywords."""
    if not loc:
        return set()
    cleaned = re.sub(r"[^\w\s]", " ", loc.lower())
    return {w for w in cleaned.split() if len(w) > 2 and w not in {"the", "and", "area", "greater"}}


def verify_identity_pair(
    li: dict,
    ig: Optional[InstagramProfileCandidate]
) -> Tuple[str, str, str, Optional[str]]:
    """
    Strict identity pairing verification.
    
    Returns:
        (status, verification_method, verification_evidence, rejection_reason)
    """
    if not ig:
        return (
            "pairing_failed",
            "none",
            "",
            "No corresponding Instagram profile could be found for this LinkedIn candidate."
        )

    if ig.is_private:
        return (
            "rejected",
            "none",
            "",
            f"Instagram profile @{ig.username} is private. AgentDate requires public profiles."
        )

    li_handle = li.get("handle", "").lower()
    li_url = li.get("url", "").lower()
    ig_bio = (ig.bio or "").lower()
    ig_link = (ig.external_url or "").lower()
    li_headline = (li.get("headline") or "").lower()

    # Rule 1: Direct Cross-Link Verification (Gold Standard for Autonomous Approval)
    # Check if Instagram bio or external URL explicitly links to this LinkedIn profile
    has_crosslink = False
    crosslink_note = ""

    if li_handle and (li_handle in ig_link or f"linkedin.com/in/{li_handle}" in ig_bio):
        has_crosslink = True
        crosslink_note = f"Direct cross-link verified: Instagram bio/link directly references LinkedIn profile ({li_handle})"
    elif f"@{ig.username.lower()}" in li_headline:
        has_crosslink = True
        crosslink_note = f"Direct cross-link verified: LinkedIn profile headline directly references @{ig.username}"


    if has_crosslink:
        return (
            "verified_crosslink",
            "direct_crosslink",
            crosslink_note,
            None
        )

    # Rule 2: Check for explicit contradictions (Location mismatch, opposing professional domains)
    li_loc_tokens = _extract_cities(li.get("location", ""))
    ig_loc_tokens = _extract_cities(ig.location)

    # If both specified explicit locations and have zero token overlap
    if li_loc_tokens and ig_loc_tokens and not (li_loc_tokens & ig_loc_tokens):
        return (
            "rejected",
            "none",
            "",
            f"Contradictory location: LinkedIn states '{li.get('location')}' while Instagram indicates '{ig.location}'."
        )

    # Rule 3: Ambiguous Pairs (Never auto-enroll: requires explicit human signoff)
    # Even if name and city align, without a direct cross-link identity is uncertain.
    return (
        "requires_human_verification",
        "none",
        "",
        "Matching name and city observed, but no direct cross-link found. Human verification required before invitation."
    )
