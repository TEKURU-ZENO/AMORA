from __future__ import annotations

import hashlib
import uuid
from typing import Callable, Optional

from .. import store
from .models import DiscoveryCandidate
from .pairing import find_candidate_instagram
from .registry import get_candidate, list_candidates, save_candidate
from .search import search_linkedin
from .verification import verify_identity_pair


def _candidate_id(li_handle: str) -> str:
    """Deterministic candidate ID based on normalized LinkedIn handle."""
    return f"cand_{hashlib.sha256(li_handle.strip().lower().encode('utf-8')).hexdigest()[:12]}"


def run_discovery_batch(
    query: str = "",
    limit: int = 10,
    progress: Optional[Callable[[str | dict], None]] = None
) -> list[DiscoveryCandidate]:
    """
    Coordinates candidate discovery: search -> deduplicate -> pair -> verify -> register.
    """
    def log(msg: str | dict):
        if progress:
            progress(msg)

    log(f"Starting candidate discovery search (query='{query}', limit={limit})")
    log({"type": "discovery_start", "query": query, "limit": limit})

    found_li = search_linkedin(query, limit=limit)
    log(f"Found {len(found_li)} potential LinkedIn profiles from search")

    # Get already enrolled people to prevent re-discovering active pool participants
    existing_persons = {p.linkedin_url.lower() for p in store.list_persons()}
    results: list[DiscoveryCandidate] = []

    for li in found_li:
        norm_url = li["url"].lower()
        if norm_url in existing_persons:
            log(f"Skipping {li['name']}: already enrolled in AMORA pool")
            continue

        cid = _candidate_id(li["handle"])
        existing_cand = get_candidate(cid)
        if existing_cand and existing_cand.status in ("consented", "declined", "invited"):
            results.append(existing_cand)
            continue

        log(f"Searching Instagram pairing for {li['name']} ({li['handle']})")
        ig = find_candidate_instagram(li)
        status, method, evidence, rejection = verify_identity_pair(li, ig)

        token = None
        if status == "verified_crosslink":
            token = f"inv_{uuid.uuid4().hex[:16]}"

        cand = DiscoveryCandidate(
            id=cid,
            linkedin_url=li["url"],
            linkedin_handle=li["handle"],
            linkedin_name=li["name"],
            linkedin_headline=li.get("headline", ""),
            linkedin_location=li.get("location", ""),
            instagram_url=ig.url if ig else None,
            instagram_username=ig.username if ig else None,
            instagram_bio=ig.bio if ig else None,
            instagram_external_url=ig.external_url if ig else None,
            status=status,
            verification_method=method,
            verification_evidence=evidence,
            rejection_reason=rejection,
            invitation_token=token,
        )

        save_candidate(cand)
        results.append(cand)

        log({
            "type": "candidate_evaluated",
            "candidate_id": cand.id,
            "name": cand.linkedin_name,
            "status": cand.status,
            "verification_method": cand.verification_method,
            "evidence": cand.verification_evidence,
            "rejection": cand.rejection_reason,
            "invitation_token": cand.invitation_token,
        })
        log(f"Candidate {cand.linkedin_name}: {cand.status} ({evidence or rejection})")

    log({"type": "discovery_done", "count": len(results)})
    log(f"Discovery batch completed: {len(results)} candidates evaluated and registered")
    return results
