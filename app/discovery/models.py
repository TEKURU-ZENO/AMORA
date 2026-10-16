from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field


class DiscoveryCandidate(BaseModel):
    id: str
    linkedin_url: str
    linkedin_handle: str
    linkedin_name: str
    linkedin_headline: str = ""
    linkedin_location: str = ""
    instagram_url: Optional[str] = None
    instagram_username: Optional[str] = None
    instagram_bio: Optional[str] = None
    instagram_external_url: Optional[str] = None
    status: Literal[
        "discovered",
        "pairing_failed",
        "rejected",
        "requires_human_verification",
        "verified_crosslink",
        "invited",
        "consented",
        "declined"
    ] = "discovered"
    verification_method: Literal["direct_crosslink", "human_review", "none"] = "none"
    verification_evidence: str = ""
    rejection_reason: Optional[str] = None
    invitation_token: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
