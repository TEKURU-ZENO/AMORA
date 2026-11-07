"""Tests for AMORA SaaS Notification Center, Match Alerts, and Tier Quota Gating."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import harness, notifications, store
from app.main import app
from app.models import DateRecord, Verdict
from app.saas import create_or_get_user, create_session, get_user, save_user, set_session_cookie
from tests.conftest import seed_pool


@pytest.fixture(scope="module", autouse=True)
def setup_notifications_suite():
    store.init()
    store.clear_all()
    seed_pool(4)
    harness.run_round(progress=lambda m: None)


def test_notification_crud_operations():
    """Verify notification creation, listing, unread counting, and marking read."""
    user = create_or_get_user("notif_tester@amora.date", name="Elena Rostova", plan="free")

    # 1. Create notification
    n1 = notifications.create_notification(
        user_id=user.id,
        title="★ Stable Match Found",
        message="Your agent formed an Irving stable match with Liam Vance.",
        type="stable_match",
        link="/my-agent",
    )
    assert n1.id.startswith("notif_")
    assert n1.is_read is False

    n2 = notifications.create_notification(
        user_id=user.id,
        title="Dealbreaker Protected",
        message="Agent declined a date due to incompatible pace.",
        type="dealbreaker_alert",
    )

    # 2. Unread count
    unread = notifications.count_unread_notifications(user.id)
    assert unread >= 2

    # 3. List notifications
    notifs = notifications.list_notifications(user.id)
    assert len(notifs) >= 2
    assert notifs[0].id == n2.id  # Newest first

    # 4. Mark single read
    ok = notifications.mark_as_read(n2.id, user.id)
    assert ok is True
    assert notifications.count_unread_notifications(user.id) == unread - 1

    # 5. Mark all read
    marked_count = notifications.mark_all_as_read(user.id)
    assert marked_count >= 1
    assert notifications.count_unread_notifications(user.id) == 0


def test_dispatch_round_notifications():
    """Verify automated notification generation when dates and stable matches complete."""
    people = store.list_persons()
    assert len(people) >= 2
    p1 = people[0]
    p2 = people[1]

    user = create_or_get_user("round_notif_user@amora.date", name="David Kim", plan="pro", person_id=p1.id)

    # Synthetic mock date with dealbreaker hit
    d_mock = DateRecord(
        id=f"date_{p1.id}_{p2.id}",
        engine="offline",
        a=p1.id,
        b=p2.id,
        venue="The Interval",
        venue_reason="Test venue",
        turns=[],
        verdict_a=Verdict(
            agent_for=p1.id,
            score=2.0,
            chemistry=2.0,
            needs_met=1.5,
            values_alignment=2.0,
            second_date=False,
            dealbreaker_hit=True,
            reasons=["Incompatible values"],
            report_to_human="Dealbreaker hit regarding pacing.",
        ),
        verdict_b=Verdict(
            agent_for=p2.id,
            score=7.0,
            chemistry=7.0,
            needs_met=6.5,
            values_alignment=7.5,
            second_date=True,
            dealbreaker_hit=False,
            reasons=["Nice chemistry"],
            report_to_human="Enjoyable date.",
        ),
        mutual=3.1,
    )

    dispatched = notifications.dispatch_round_notifications([d_mock])
    assert dispatched >= 1

    user_notifs = notifications.list_notifications(user.id)
    assert any("Dealbreaker Protected" in n.title for n in user_notifs)


def test_notification_http_endpoints():
    """Verify HTTP views and API endpoints for notifications."""
    client = TestClient(app)
    user = create_or_get_user("http_notif_user@amora.date", name="Sarah Connor", plan="pro")
    token = create_session(user.id)

    # Unauthenticated redirect
    res_unauth = client.get("/notifications", follow_redirects=False)
    assert res_unauth.status_code == 303
    assert "/login" in res_unauth.headers.get("location", "")

    # Authenticated view
    client.cookies.set("amora_session", token)
    res_auth = client.get("/notifications")
    assert res_auth.status_code == 200
    assert "Match &amp; Agent Alerts" in res_auth.text

    # Create a notification for testing API
    n = notifications.create_notification(
        user_id=user.id,
        title="Test Notification",
        message="A test message for API verification.",
        type="system",
    )

    # JSON API GET /api/notifications
    res_api = client.get("/api/notifications")
    assert res_api.status_code == 200
    data = res_api.json()
    assert data["unread_count"] >= 1
    assert any(item["id"] == n.id for item in data["notifications"])

    # POST /api/notifications/{nid}/read
    res_read = client.post(f"/api/notifications/{n.id}/read", headers={"Accept": "application/json"})
    assert res_read.status_code == 200
    assert res_read.json()["status"] == "success"

    # POST /api/notifications/read-all
    res_read_all = client.post("/api/notifications/read-all", headers={"Accept": "application/json"})
    assert res_read_all.status_code == 200
    assert "count" in res_read_all.json()


def test_tier_gating_and_quota_enforcement():
    """Verify Pro feature gating on live whispers and audio, plus date quota deduction."""
    client = TestClient(app)
    people = store.list_persons()
    dates = store.list_dates()
    assert dates, "Requires dates from seed pool"
    d = dates[0]
    p_owner = store.get_person(d.a)

    # 1. Create Free User
    free_user = create_or_get_user("free_gating@amora.date", plan="free", person_id=p_owner.id)
    free_token = create_session(free_user.id)
    client.cookies.set("amora_session", free_token)

    # Free user attempting live whisper -> 402 Payment Required
    res_whisper_free = client.post(
        f"/api/dates/{d.id}/whisper",
        data={"pid": d.a, "whisper": "Ask about coffee!", "token": p_owner.edit_token},
    )
    assert res_whisper_free.status_code == 402
    assert "exclusive to Pro and VIP" in res_whisper_free.text

    # Free user attempting audio cues -> 402 Payment Required
    res_audio_free = client.get(f"/api/dates/{d.id}/audio-cues")
    assert res_audio_free.status_code == 402
    assert "exclusive to Pro and VIP" in res_audio_free.text

    # 2. Upgrade to Pro
    free_user.plan = "pro"
    save_user(free_user)

    # Pro user attempting live whisper -> 200 Delivered
    res_whisper_pro = client.post(
        f"/api/dates/{d.id}/whisper",
        data={"pid": d.a, "whisper": "Ask about hiking!", "token": p_owner.edit_token},
    )
    assert res_whisper_pro.status_code == 200
    assert res_whisper_pro.json()["status"] == "delivered"

    # Pro user audio cues -> 200 OK
    res_audio_pro = client.get(f"/api/dates/{d.id}/audio-cues")
    assert res_audio_pro.status_code == 200
    assert isinstance(res_audio_pro.json(), list)
    assert len(res_audio_pro.json()) > 0

    # 3. Quota deduction test on create_persona
    quota_user = create_or_get_user("quota_tester@amora.date", plan="free")
    quota_user.credits_remaining = 1
    save_user(quota_user)

    q_token = create_session(quota_user.id)
    client.cookies.set("amora_session", q_token)

    # First persona creation consumes 1 credit -> succeeds
    res_persona_1 = client.post(
        "/api/saas/create-persona",
        data={
            "display_name": "Quota Tester 1",
            "one_liner": "Software Engineer · Coffee enthusiast",
            "hobbies": "Coding, Coffee",
            "dealbreakers": "Smoking",
        },
        follow_redirects=False,
    )
    assert res_persona_1.status_code == 303

    u_refreshed = get_user(quota_user.id)
    assert u_refreshed.credits_remaining == 0

    # Second persona creation with 0 credits -> 402 Payment Required
    res_persona_2 = client.post(
        "/api/saas/create-persona",
        data={
            "display_name": "Quota Tester 2",
            "one_liner": "Another Persona",
            "hobbies": "Running",
            "dealbreakers": "None",
        },
        follow_redirects=False,
    )
    assert res_persona_2.status_code == 402
    assert "Free Explorer quota" in res_persona_2.text
