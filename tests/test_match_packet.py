"""Tests for Match Packet Executive Dossier and SaaS Persona Onboarding."""
import pytest
from starlette.testclient import TestClient

from app import harness, store
from app.main import app
from app.match_packet import build_match_packet_data
from app.saas import create_or_get_user, create_session, set_session_cookie
from tests.conftest import seed_pool


@pytest.fixture(scope="module", autouse=True)
def setup_test_suite():
    store.init()
    store.clear_all()
    seed_pool(6)
    harness.run_round(progress=lambda m: None)


def test_build_match_packet_data():
    """Verify match packet dossier generation with second date plan and first fight."""
    dates = store.list_dates()
    assert len(dates) >= 1
    d = dates[0]

    packet = build_match_packet_data(d.id)
    assert packet["date_id"] == d.id
    assert "person_a" in packet
    assert "person_b" in packet
    assert packet["person_a"]["full_name"] != ""
    assert packet["person_b"]["full_name"] != ""
    assert "mutual_score" in packet
    assert "venue" in packet


def test_match_packet_http_endpoints():
    """Verify GET /date/{did}/match-packet and GET /api/dates/{did}/match-packet."""
    client = TestClient(app)
    dates = store.list_dates()
    d = dates[0]

    # HTML page
    res_html = client.get(f"/date/{d.id}/match-packet")
    assert res_html.status_code == 200
    assert "text/html" in res_html.headers.get("content-type", "")
    assert "Executive Match Dossier" in res_html.text
    assert "Print / Save PDF" in res_html.text

    # JSON API
    res_json = client.get(f"/api/dates/{d.id}/match-packet")
    assert res_json.status_code == 200
    data = res_json.json()
    assert data["date_id"] == d.id
    assert data["mutual_score"] > 0
    assert "person_a" in data
    assert "person_b" in data


def test_saas_create_persona_onboarding():
    """Verify SaaS user can create a bespoke persona and link it to their account."""
    client = TestClient(app)
    user = create_or_get_user("new_user@amora.date", name="New Founder", plan="pro")
    sess_token = create_session(user.id)
    client.cookies.set("amora_session", sess_token)

    res = client.post(
        "/api/saas/create-persona",
        data={
            "display_name": "Priya Sharma",
            "one_liner": "Product Lead & Trail Runner",
            "hobbies": "Trail Running, Ceramic Art, Specialty Coffee",
            "dealbreakers": "Smoking, Cynicism, Long-distance",
            "pace": "Active morning pace",
            "initial_coaching": "Ask what their favorite weekend escape looks like.",
        },
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers["location"] == "/my-agent"

    # Verify user is now linked to their new persona
    from app.saas import get_user
    u_updated = get_user(user.id)
    assert u_updated.person_id is not None
    assert u_updated.person_id.startswith("usr-")

    p = store.get_person(u_updated.person_id)
    assert p is not None
    assert p.analysis.display_name == "Priya Sharma"
    assert "Trail Running" in p.analysis.hobbies
    assert "Smoking" in p.analysis.dealbreakers
    assert len(p.coaching_notes) == 1

    # Verify persona has dates against the pool
    my_dates = store.list_dates(p.id)
    assert len(my_dates) >= 1
