"""Tests for AMORA SaaS Multi-Tenant Architecture, Subscriptions, and AI Icebreakers."""
from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient

from app import harness, store
from app.main import app
from app.saas import (
    can_access_planner,
    can_access_stress_test,
    can_access_voice_dates,
    can_whisper_live,
    create_checkout_session,
    create_or_get_user,
    create_session,
    delete_session,
    generate_icebreakers,
    get_user,
    get_user_by_session,
    handle_stripe_webhook,
    link_person_to_user,
    save_user,
)
from app.saas.models import User
from tests.conftest import seed_pool


@pytest.fixture(scope="module", autouse=True)
def setup_saas_suite():
    store.init()
    store.clear_all()
    seed_pool(4)
    harness.run_round(progress=lambda m: None)


def test_user_creation_and_session_lifecycle():
    """Verify passwordless user registration, session tokens, and lookup."""
    user = create_or_get_user("founder@amora.date", name="Dev M", plan="pro")
    assert user.id.startswith("usr_")
    assert user.email == "founder@amora.date"
    assert user.plan == "pro"
    assert user.is_pro_or_vip is True

    # Session token
    token = create_session(user.id)
    assert token.startswith("sess_")

    # Session lookup
    fetched = get_user_by_session(token)
    assert fetched is not None
    assert fetched.id == user.id
    assert fetched.email == "founder@amora.date"

    # Invalidate session
    delete_session(token)
    assert get_user_by_session(token) is None


def test_persona_linking_and_feature_gates():
    """Verify linking persona to user and SaaS tier entitlements."""
    people = store.list_persons()
    assert len(people) >= 2
    p1 = people[0]

    free_user = create_or_get_user("free_user@amora.date", plan="free")
    link_person_to_user(free_user.id, p1.id)
    u_updated = get_user(free_user.id)
    assert u_updated.person_id == p1.id

    # Free tier entitlements
    assert can_access_voice_dates(u_updated) is False
    assert can_access_stress_test(u_updated) is False
    assert can_whisper_live(u_updated) is False

    # Upgrade to Pro
    u_updated.plan = "pro"
    save_user(u_updated)
    assert can_access_voice_dates(u_updated) is True
    assert can_access_stress_test(u_updated) is True
    assert can_access_planner(u_updated) is True
    assert can_whisper_live(u_updated) is True


def test_ai_icebreaker_generation():
    """Verify AI icebreaker suggestions for matches."""
    people = store.list_persons()
    assert len(people) >= 2
    pa, pb = people[0], people[1]

    # Find or simulate date between them
    dates = store.list_dates()
    d_rec = dates[0] if dates else None

    suggestions = generate_icebreakers(pa, pb, d_rec)
    assert len(suggestions) == 3

    styles = [s.style for s in suggestions]
    assert "witty_callback" in styles
    assert "shared_passion" in styles
    assert "direct_invite" in styles

    for s in suggestions:
        assert s.message != ""
        assert s.headline != ""
        assert s.target_name != ""


def test_billing_checkout_and_webhooks():
    """Verify checkout creation and Stripe lifecycle webhooks."""
    user = create_or_get_user("billing_tester@amora.date", plan="free")

    # Test checkout session creation (instant mock upgrade when no live Stripe key)
    checkout = create_checkout_session(
        user=user,
        plan="pro",
        success_url="http://localhost:8000/pricing?upgraded=pro",
        cancel_url="http://localhost:8000/pricing",
    )
    assert "url" in checkout
    assert "session_id" in checkout

    u_pro = get_user(user.id)
    assert u_pro.plan == "pro"

    # Test webhook: customer.subscription.deleted downgrades to free
    webhook_payload = json.dumps({
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": u_pro.stripe_subscription_id or "sub_demo_pro_" + user.id,
                "customer": u_pro.stripe_customer_id,
            }
        }
    }).encode("utf-8")

    res = handle_stripe_webhook(webhook_payload)
    assert res["status"] == "downgraded"

    u_downgraded = get_user(user.id)
    assert u_downgraded.plan == "free"


def test_saas_http_endpoints():
    """Verify HTTP endpoints for login, pricing, dashboard, and billing."""
    client = TestClient(app)

    # 1. GET /pricing
    res_pricing = client.get("/pricing")
    assert res_pricing.status_code == 200
    assert "Hire Your Autonomous Matchmaker" in res_pricing.text
    assert "Pro Matchmaker" in res_pricing.text

    # 2. GET /login
    res_login = client.get("/login")
    assert res_login.status_code == 200
    assert "Welcome Back" in res_login.text
    assert "Demo: Maya Patel" in res_login.text

    # 3. POST /login with demo credentials
    res_auth = client.post(
        "/login",
        data={
            "email": "maya.patel@stripe.demo",
            "name": "Maya Patel",
            "demo_plan": "pro",
            "claim_name": "Maya",
            "next": "/my-agent",
        },
        follow_redirects=False,
    )
    assert res_auth.status_code == 303
    assert "amora_session" in res_auth.headers.get("set-cookie", "")

    # Extract session cookie
    cookie = res_auth.cookies.get("amora_session")
    assert cookie is not None

    # 4. GET /my-agent with session cookie
    res_dash = client.get("/my-agent", cookies={"amora_session": cookie})
    assert res_dash.status_code == 200
    assert "Autonomous Dating Dashboard" in res_dash.text
    assert "PRO MATCHMAKER" in res_dash.text

    # 5. POST /api/billing/checkout
    res_upgrade = client.post(
        "/api/billing/checkout",
        data={"plan": "vip"},
        cookies={"amora_session": cookie},
        follow_redirects=False,
    )
    assert res_upgrade.status_code == 303
    assert "upgraded=vip" in res_upgrade.headers.get("location", "")

    # 6. GET /logout
    res_logout = client.get("/logout", cookies={"amora_session": cookie}, follow_redirects=False)
    assert res_logout.status_code == 303
