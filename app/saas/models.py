"""Data models for AMORA SaaS multi-tenant infrastructure.

Includes:
- User accounts and subscription tiers (Free, Pro, VIP).
- Agent ownership and multi-tenant profile links.
- AI-drafted first message / icebreaker suggestions.
- Billing and usage telemetry.
"""
from __future__ import annotations

import time
from typing import Literal, Optional
from pydantic import BaseModel, Field


PlanTier = Literal["free", "pro", "vip"]


class User(BaseModel):
    id: str
    email: str
    name: str = ""
    person_id: Optional[str] = None  # The persona owned/claimed by this user
    plan: PlanTier = "free"
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()))
    credits_remaining: int = 5
    is_active: bool = True

    @property
    def is_pro_or_vip(self) -> bool:
        return self.plan in ("pro", "vip")

    @property
    def is_vip(self) -> bool:
        return self.plan == "vip"

    @property
    def plan_label(self) -> str:
        if self.plan == "vip":
            return "VIP Matchmaker"
        elif self.plan == "pro":
            return "Pro Matchmaker"
        return "Free Explorer"


class IcebreakerSuggestion(BaseModel):
    style: Literal["witty_callback", "shared_passion", "direct_invite"]
    headline: str
    message: str
    target_name: str
    target_handle: str = ""
    platform_hint: str = "Instagram / WhatsApp"
    instagram_dm_url: Optional[str] = None
    linkedin_url: Optional[str] = None


class UserProfileClaimRequest(BaseModel):
    person_id: str


class UpgradePlanRequest(BaseModel):
    plan: PlanTier
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
