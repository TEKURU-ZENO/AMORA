import os
import pytest
from fastapi.testclient import TestClient


from app import config, harness, store
from app.main import app
from tests.conftest import seed_pool




@pytest.fixture(scope="module", autouse=True)
def seed_test_data():
    store.init()
    store.clear_all()
    seed_pool(6)
    harness.run_round(progress=lambda m: None)



def test_unauthenticated_export_sanitized():
    client = TestClient(app)
    res = client.get("/api/export")
    assert res.status_code == 200
    data = res.json()
    assert "people" in data and "dates" in data and "rankings" in data
    assert len(data["dates"]) > 0

    # Ensure zero private thoughts and sanitized reports in public export
    for d in data["dates"]:
        for turn in d["turns"]:
            assert turn.get("thought") == "", f"Private thought leaked in public export: {turn}"
        assert d["verdict_a"]["report_to_human"] == "[Private agent report to human]"
        assert d["verdict_b"]["report_to_human"] == "[Private agent report to human]"

    # Ensure raw sources excluded from people
    for p in data["people"]:
        assert "sources" not in p or p["sources"] is None


def test_admin_export_access_control():
    client = TestClient(app)
    # Unauthorized request rejected with 401
    unauth = client.get("/api/admin/export")
    assert unauth.status_code == 401

    bad_key = client.get("/api/admin/export", headers={"X-AgentDate-Key": "wrong-key"})
    assert bad_key.status_code == 401

    # Authorized with header
    auth_header = client.get("/api/admin/export", headers={"X-AgentDate-Key": "test-secret-key-123"})
    assert auth_header.status_code == 200
    dates = auth_header.json()["dates"]
    assert len(dates) > 0
    # Thoughts are preserved for authorized audit
    has_thought = any(any(bool(t.get("thought")) for t in d["turns"]) for d in dates)
    assert has_thought, "Authorized export should retain private thoughts"

    # Authorized with query param
    auth_param = client.get("/api/admin/export?demo_key=test-secret-key-123")
    assert auth_param.status_code == 200


def test_date_replay_privacy_boundary():
    client = TestClient(app)
    date = store.list_dates()[0]
    # Unsanitized date record in storage has thoughts
    assert any(bool(t.thought) for t in date.turns)
    stored_thought = next(t.thought for t in date.turns if t.thought)

    # Public replay: thoughts must not appear in HTML
    res_pub = client.get(f"/date/{date.id}")
    assert res_pub.status_code == 200
    html_pub = res_pub.text
    assert "🔒 Private thoughts hidden" in html_pub
    assert stored_thought not in html_pub

    # Authorized demo replay: thoughts should appear
    res_auth = client.get(f"/date/{date.id}?demo_key=test-secret-key-123")
    assert res_auth.status_code == 200
    html_auth = res_auth.text
    assert "Authorized Demo" in html_auth
    assert stored_thought in html_auth


def test_consent_revocation_lifecycle():
    client = TestClient(app)
    people = store.list_persons()
    target = [p for p in people if store.list_dates(p.id)][0]

    # Verify target initially has dates
    initial_dates = store.list_dates(target.id)
    assert len(initial_dates) > 0


    # Revoke consent
    res = client.post(f"/person/{target.id}/revoke-consent")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "revoked"
    assert body["person"] == target.id

    # Verify person consent is False and status error
    updated = store.get_person(target.id)
    assert updated is not None
    assert updated.consent is False
    assert "revoked" in updated.error.lower()

    # Verify all dates involving target are purged
    assert len(store.list_dates(target.id)) == 0
    for d in store.list_dates():
        assert d.a != target.id and d.b != target.id


def test_cascading_deletion():
    client = TestClient(app)
    people = store.list_persons()
    # Pick a person who still has dates
    target = [p for p in people if store.list_dates(p.id)][0]
    pid = target.id

    # Delete person
    res = client.post(f"/person/{pid}/delete", follow_redirects=False)
    assert res.status_code == 303

    # Assert completely purged
    assert store.get_person(pid) is None
    assert len(store.list_dates(pid)) == 0

    # Assert purged from asks and rankings meta
    asks = store.get_meta("asks", {})
    assert pid not in asks
    for p_asks in asks.values():
        assert all(t[0] != pid for t in p_asks)

    rankings = store.get_meta("rankings", {})
    assert pid not in rankings
    for p_rows in rankings.values():
        assert all(r.get("id") != pid for r in p_rows)
