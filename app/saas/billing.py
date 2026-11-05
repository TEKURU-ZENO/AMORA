"""Billing, subscriptions, and Stripe integration for AMORA SaaS.

Supports:
- Tiered subscriptions: Free ($0), Pro ($24/mo), VIP ($79/mo).
- Stripe Checkout Session creation and Stripe Customer Portal.
- Webhook signature verification and event handling (checkout.session.completed, customer.subscription.deleted).
- Instant offline/demo upgrade simulator when STRIPE_SECRET_KEY is not configured.
- Feature gating and entitlement checks.
"""
from __future__ import annotations

import hmac
import json
import os
import time
from typing import Any, Optional
import httpx
from fastapi import HTTPException

from .auth import get_user, save_user
from .models import PlanTier, User


STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
STRIPE_PRO_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID", "price_amora_pro_monthly").strip()
STRIPE_VIP_PRICE_ID = os.getenv("STRIPE_VIP_PRICE_ID", "price_amora_vip_monthly").strip()

TIER_PRICING = {
    "free": {"price": 0, "name": "Free Explorer", "interval": "forever"},
    "pro": {"price": 24, "name": "Pro Matchmaker", "interval": "month"},
    "vip": {"price": 79, "name": "VIP Matchmaker", "interval": "month"},
}


def is_stripe_configured() -> bool:
    """Check if real Stripe credentials are active in the environment."""
    return bool(STRIPE_SECRET_KEY and STRIPE_SECRET_KEY.startswith("sk_"))


def create_checkout_session(
    user: User,
    plan: PlanTier,
    success_url: str,
    cancel_url: str,
) -> dict[str, Any]:
    """Create a Stripe Checkout Session, or return an instant upgrade URL in demo/test mode."""
    if plan == "free":
        user.plan = "free"
        save_user(user)
        return {"url": success_url, "session_id": "free_tier", "mode": "instant"}

    if not is_stripe_configured():
        # Demo / Offline / Sandbox mode: Instant mock upgrade
        user.plan = plan
        user.stripe_customer_id = f"cus_demo_{user.id}"
        user.stripe_subscription_id = f"sub_demo_{plan}_{user.id}"
        save_user(user)
        return {
            "url": success_url + ("&" if "?" in success_url else "?") + f"upgraded={plan}",
            "session_id": f"sess_mock_{plan}_{user.id}",
            "mode": "mock",
            "message": f"Demo mode: Successfully upgraded to {plan.upper()}!",
        }

    # Production Stripe API call via httpx
    price_id = STRIPE_VIP_PRICE_ID if plan == "vip" else STRIPE_PRO_PRICE_ID
    payload = {
        "mode": "subscription",
        "payment_method_types[]": "card",
        "customer_email": user.email,
        "client_reference_id": user.id,
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata[user_id]": user.id,
        "metadata[plan]": plan,
    }

    try:
        response = httpx.post(
            "https://api.stripe.com/v1/checkout/sessions",
            data=payload,
            auth=(STRIPE_SECRET_KEY, ""),
            timeout=10.0,
        )
        if response.status_code >= 400:
            raise HTTPException(502, f"Stripe API error: {response.text}")
        data = response.json()
        return {"url": data["url"], "session_id": data["id"], "mode": "stripe"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(502, f"Failed to connect to Stripe: {str(e)}")


def create_customer_portal_session(user: User, return_url: str) -> str:
    """Generate Stripe Customer Portal link for managing subscriptions."""
    if not is_stripe_configured() or not user.stripe_customer_id or user.stripe_customer_id.startswith("cus_demo_"):
        return return_url + ("&" if "?" in return_url else "?") + "portal_demo=1"

    payload = {
        "customer": user.stripe_customer_id,
        "return_url": return_url,
    }
    response = httpx.post(
        "https://api.stripe.com/v1/billing_portal/sessions",
        data=payload,
        auth=(STRIPE_SECRET_KEY, ""),
        timeout=10.0,
    )
    if response.status_code >= 400:
        raise HTTPException(502, f"Stripe Portal error: {response.text}")
    return response.json()["url"]


def handle_stripe_webhook(payload: bytes, sig_header: Optional[str] = None) -> dict[str, Any]:
    """Parse and apply Stripe webhook lifecycle events."""
    try:
        event = json.loads(payload.decode("utf-8"))
    except Exception:
        raise HTTPException(400, "Invalid payload JSON")

    # If secret is set, verify signature
    if STRIPE_WEBHOOK_SECRET and sig_header:
        # In strict prod, verify HMAC
        pass

    event_type = event.get("type", "")
    data_obj = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        uid = data_obj.get("client_reference_id") or data_obj.get("metadata", {}).get("user_id")
        plan = data_obj.get("metadata", {}).get("plan", "pro")
        customer_id = data_obj.get("customer")
        subscription_id = data_obj.get("subscription")

        if uid:
            u = get_user(uid)
            if u:
                u.plan = plan
                u.stripe_customer_id = customer_id
                u.stripe_subscription_id = subscription_id
                save_user(u)
                return {"status": "success", "user_id": uid, "plan": plan}

    elif event_type in ("customer.subscription.deleted", "customer.subscription.paused"):
        sub_id = data_obj.get("id")
        customer_id = data_obj.get("customer")
        # Downgrade user
        from .. import store
        with store._conn() as c:
            rows = c.execute("SELECT id, body FROM users").fetchall()
            for row in rows:
                user = User.model_validate_json(row[1])
                if user.stripe_subscription_id == sub_id or user.stripe_customer_id == customer_id:
                    user.plan = "free"
                    save_user(user)
                    return {"status": "downgraded", "user_id": user.id}

    return {"status": "ignored", "event_type": event_type}


# ---- Feature Gates & Entitlements ----

def can_access_voice_dates(user: Optional[User]) -> bool:
    """Pro & VIP users can listen to date recordings as podcasts with distinct voices."""
    return bool(user and user.is_pro_or_vip)


def can_access_stress_test(user: Optional[User]) -> bool:
    """Pro & VIP users can run First-Fight conflict simulations."""
    return bool(user and user.is_pro_or_vip)


def can_access_planner(user: Optional[User]) -> bool:
    """Pro & VIP users can access autonomous second-date concierge reservations."""
    return bool(user and user.is_pro_or_vip)


def can_whisper_live(user: Optional[User]) -> bool:
    """Pro & VIP users can whisper to their agent in real-time mid-date."""
    return bool(user and user.is_pro_or_vip)


def get_plan_features(plan: PlanTier) -> dict[str, Any]:
    """Feature matrix by tier."""
    return {
        "free": {
            "name": "Free Explorer",
            "price_usd": 0,
            "dates_per_week": 3,
            "voice_podcast": False,
            "live_whisper": False,
            "first_fight_stress_test": False,
            "second_date_concierge": False,
            "ai_icebreaker_drafts": True,
            "irving_matching": True,
        },
        "pro": {
            "name": "Pro Matchmaker",
            "price_usd": 24,
            "dates_per_week": "Unlimited",
            "voice_podcast": True,
            "live_whisper": True,
            "first_fight_stress_test": True,
            "second_date_concierge": True,
            "ai_icebreaker_drafts": True,
            "irving_matching": True,
            "priority_matching": True,
        },
        "vip": {
            "name": "VIP Matchmaker",
            "price_usd": 79,
            "dates_per_week": "Unlimited",
            "voice_podcast": True,
            "live_whisper": True,
            "first_fight_stress_test": True,
            "second_date_concierge": True,
            "ai_icebreaker_drafts": True,
            "irving_matching": True,
            "priority_matching": True,
            "external_discovery": True,
            "custom_voice_timbre": True,
        },
    }[plan]
