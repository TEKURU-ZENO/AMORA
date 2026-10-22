import pytest
from fastapi.testclient import TestClient

from app import config, harness, store
from app.agents import coaching
from app.agents.dater import go_on_date
from app.main import app
from tests.conftest import seed_pool


@pytest.fixture(scope="module", autouse=True)
def setup_coaching_suite():
    store.init()
    store.clear_all()
    seed_pool(8)
    harness.run_round(progress=lambda m: None)


def test_predate_coaching_directives():
    client = TestClient(app)
    people = [p for p in store.list_persons() if p.analysis]
    assert len(people) >= 2
    p1 = people[0]

    # 1. Endpoint: Add coaching directive
    res = client.post(f"/person/{p1.id}/coach", data={
        "action": "add",
        "note": "Ask if they would ever move abroad in the future"
    }, follow_redirects=False)
    assert res.status_code == 303

    p1_updated = store.get_person(p1.id)
    assert "Ask if they would ever move abroad in the future" in p1_updated.coaching_notes

    # 2. Add second directive
    client.post(f"/person/{p1.id}/coach", data={
        "action": "add",
        "note": "Strictly do not bring up work or career talk"
    }, follow_redirects=False)

    p1_updated = store.get_person(p1.id)
    assert len(p1_updated.coaching_notes) == 2

    # 3. Test conversation includes coaching
    p2 = people[1]
    date_record = go_on_date(p1.id, p1_updated.analysis, p2.id, p2.analysis,
                             coaching_a=p1_updated.coaching_notes)
    
    # Check that turns or thoughts reflect the coaching
    coached_turn = any(
        "abroad" in t.text.lower() or "abroad" in t.thought.lower() or
        "work" in t.text.lower() or "work" in t.thought.lower()
        for t in date_record.turns if t.speaker == p1.id
    )
    assert coached_turn, "Agent should follow coaching directives during conversation"

    # 4. Endpoint: Remove coaching directive
    res_rem = client.post(f"/person/{p1.id}/coach", data={
        "action": "remove",
        "index": 0
    }, follow_redirects=False)
    assert res_rem.status_code == 303
    p1_after_rem = store.get_person(p1.id)
    assert len(p1_after_rem.coaching_notes) == 1
    assert "work" in p1_after_rem.coaching_notes[0].lower()


def test_per_turn_running_observations_and_verdict_discoveries():
    dates = store.list_dates()
    assert len(dates) > 0
    d = dates[0]

    # Every turn has an observation
    assert len(d.turns) >= 8
    for t in d.turns:
        assert isinstance(t.observation, str) and len(t.observation) > 0, f"Turn missing observation: {t}"

    # Date record aggregates observations
    assert len(d.observations_a) > 0
    assert len(d.observations_b) > 0

    # Verdicts contain learned_about_other revelations
    assert len(d.verdict_a.learned_about_other) >= 2
    assert len(d.verdict_b.learned_about_other) >= 2
    assert any("priority" in x.lower() or "communication" in x.lower() or "lifestyle" in x.lower()
               for x in d.verdict_a.learned_about_other)


def test_postdate_feedback_loop_and_reranking():
    client = TestClient(app)
    people = [p for p in store.list_persons() if p.analysis]
    p = people[0]

    initial_dealbreakers = list(p.analysis.dealbreakers)
    initial_rankings = store.get_meta("rankings", {}).get(p.id, [])

    # Post feedback: "you got me wrong, I hate clubs and need someone who loves outdoors"
    res = client.post(f"/person/{p.id}/feedback", data={
        "feedback": "You got me wrong, I hate clubs and wild nightlife. Need someone who loves quiet hiking."
    }, follow_redirects=False)
    assert res.status_code == 303

    p_updated = store.get_person(p.id)
    # 1. Dealbreaker added
    assert any("club" in db.lower() for db in p_updated.analysis.dealbreakers)
    assert len(p_updated.analysis.dealbreakers) > len(initial_dealbreakers)

    # 2. Need added
    assert any("hiking" in n.lower() or "quiet" in n.lower() for n in p_updated.analysis.needs)

    # 3. Feedback history logged
    assert len(p_updated.feedback_history) >= 1
    latest_fb = p_updated.feedback_history[-1]
    assert "clubs" in latest_fb["feedback"].lower()
    assert len(latest_fb["changes"]) > 0

    # 4. Rankings recomputed
    updated_rankings = store.get_meta("rankings", {}).get(p.id, [])
    assert updated_rankings, "Rankings must be recomputed after feedback"


def test_date_feedback_endpoint():
    client = TestClient(app)
    dates = store.list_dates()
    d = dates[0]
    p_a = store.get_person(d.a)

    res = client.post(f"/date/{d.id}/feedback", data={
        "pid": p_a.id,
        "feedback": "Dealbreaker: smokers. I can never date someone who smokes."
    }, follow_redirects=False)
    assert res.status_code == 303

    p_a_updated = store.get_person(d.a)
    assert any("smok" in db.lower() for db in p_a_updated.analysis.dealbreakers)
    assert p_a_updated.feedback_history[-1]["date_id"] == d.id


def test_crossdate_agent_learning_accumulation():
    people = [p for p in store.list_persons() if p.analysis]
    p = people[0]
    p_dates = store.list_dates(p.id)
    assert len(p_dates) > 0

    learnings = coaching.reflect_on_dates(p, p_dates, people)
    assert len(learnings) >= 1
    assert any("chemistry" in l.lower() or "dealbreaker" in l.lower() or "divergence" in l.lower() or "selective" in l.lower()
               for l in learnings)
    assert p.dating_learnings == learnings


def test_privacy_boundary_for_coaching_and_observations():
    client = TestClient(app)
    d = store.list_dates()[0]
    p = store.get_person(d.a)

    # 1. Public Replay: running reads and date discoveries are hidden
    res_pub = client.get(f"/date/{d.id}")
    assert res_pub.status_code == 200
    assert "🔒 Private agent discoveries masked" in res_pub.text
    # Ensure unmasked observation text isn't in public output
    assert "Running read:" not in res_pub.text

    # 2. Authorized Replay: reveals running read and date discoveries
    res_auth = client.get(f"/date/{d.id}?demo_key=test-secret-key-123")
    assert res_auth.status_code == 200
    assert "Date Discoveries on" in res_auth.text
    assert "Running read:" in res_auth.text

    # 3. Export Privacy:
    # Public export strips coaching_notes and feedback_history
    res_export = client.get("/api/export")
    assert res_export.status_code == 200
    pub_people = res_export.json()["people"]
    for pers in pub_people:
        assert "coaching_notes" not in pers or pers["coaching_notes"] is None
        assert "feedback_history" not in pers or pers["feedback_history"] is None

    # Admin export preserves them
    res_admin = client.get("/api/admin/export", headers={"X-AgentDate-Key": "test-secret-key-123"})
    assert res_admin.status_code == 200
    admin_people = res_admin.json()["people"]
    admin_target = next(pers for pers in admin_people if pers["id"] == p.id)
    assert "coaching_notes" in admin_target or "feedback_history" in admin_target
