import pytest
from fastapi.testclient import TestClient

from app import config, harness, store
from app.agents import stress
from app.main import app
from tests.conftest import seed_pool


@pytest.fixture(scope="module", autouse=True)
def setup_stress_suite():
    store.init()
    store.clear_all()
    seed_pool(6)
    harness.run_round(progress=lambda m: None)


def test_scenario_selection():
    people = [p for p in store.list_persons() if p.analysis]
    assert len(people) >= 2
    pa, pb = people[0], people[1]

    title, prompt = stress.pick_scenario(pa.analysis, pb.analysis)
    assert isinstance(title, str) and len(title) > 0
    assert isinstance(prompt, str) and len(prompt) > 0
    assert any(keyword in title.lower() for keyword in ["relocation", "energy", "financial", "pressure", "communication"])


def test_first_fight_offline_simulation():
    dates = store.list_dates()
    assert len(dates) > 0
    d = dates[0]
    pa = store.get_person(d.a)
    pb = store.get_person(d.b)

    record = stress.simulate_first_fight(d, pa, pb)
    assert record.id == f"ff_{d.id}"
    assert record.date_id == d.id
    assert len(record.turns) == 6

    # Verify each turn has text, thought, and a valid emotional tone
    valid_tones = {"vulnerable", "firm", "empathetic", "collaborative", "conciliatory", "defensive", "curious", "open", "guarded"}
    for t in record.turns:
        assert len(t.text) > 0
        assert len(t.thought) > 0
        assert t.emotional_tone in valid_tones

    # Verify verdicts
    assert 0 <= record.verdict_a.resilience_score <= 10
    assert 0 <= record.verdict_b.resilience_score <= 10
    assert record.verdict_a.stress_verdict in ("passed", "conditional", "failed")
    assert record.verdict_b.stress_verdict in ("passed", "conditional", "failed")
    assert record.outcome in ("stronger_together", "navigable_compromise", "irreconcilable_friction")
    assert 0 <= record.mutual_resilience <= 10


def test_first_fight_endpoint_and_storage():
    client = TestClient(app)
    dates = store.list_dates()
    d = dates[0]

    # Trigger via endpoint
    res = client.post(f"/date/{d.id}/first-fight", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == f"/date/{d.id}#first-fight"

    # Verify persisted in database
    d_saved = store.get_date(d.id)
    assert d_saved.first_fight is not None
    assert d_saved.first_fight.date_id == d.id

    # Verify rendered on date page
    res_page = client.get(f"/date/{d.id}")
    assert res_page.status_code == 200
    assert "The \"First Fight\": Compatibility Under Stress" in res_page.text
    assert d_saved.first_fight.scenario_title in res_page.text
    assert "Mutual Conflict Resilience" in res_page.text


def test_first_fight_privacy_boundary():
    client = TestClient(app)
    dates = store.list_dates()
    d = dates[0]
    pa = store.get_person(d.a)
    pb = store.get_person(d.b)

    stress.simulate_first_fight(d, pa, pb)
    store.save_date(d)

    stored_thought = d.first_fight.turns[0].thought
    assert len(stored_thought) > 0

    # 1. Public view masks inner reactions
    res_pub = client.get(f"/date/{d.id}")
    assert res_pub.status_code == 200
    assert "Inner reaction:" not in res_pub.text
    assert stored_thought not in res_pub.text

    # 2. Authorized view reveals inner reactions
    res_auth = client.get(f"/date/{d.id}?demo_key=test-secret-key-123")
    assert res_auth.status_code == 200
    assert "Inner reaction:" in res_auth.text
    assert stored_thought in res_auth.text


def test_round_auto_triggers_stress_for_mutual_yes():
    dates = store.list_dates()
    mutual_yes_dates = [d for d in dates if d.verdict_a.second_date and d.verdict_b.second_date]
    if mutual_yes_dates:
        # Round auto-generated first fight for mutual second date pairs
        for d in mutual_yes_dates:
            assert d.first_fight is not None
            assert d.first_fight.mutual_resilience > 0
