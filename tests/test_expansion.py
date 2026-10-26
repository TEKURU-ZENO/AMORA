import html
import pytest
from fastapi.testclient import TestClient

from app import config, harness, store
from app.agents import group_dater, judge, planner
from app.matching import gale_shapley
from app.main import app
from tests.conftest import seed_pool


@pytest.fixture(scope="module", autouse=True)
def setup_expansion_suite():
    store.init()
    store.clear_all()
    seed_pool(8)
    harness.run_round(progress=lambda m: None)


# ---------------------------------------------------------------- 1. Gale-Shapley
def test_gale_shapley_stable_matching():
    client = TestClient(app)
    result = gale_shapley.compute_stable_matching()

    assert result.total_people >= 6
    assert len(result.pairs) > 0
    assert result.stability_percentage >= 80.0

    # Verify no blocking pairs among matched
    p = result.pairs[0]
    assert p.rank_a_for_b >= 1
    assert p.rank_b_for_a >= 1
    assert p.mutual_score > 0
    assert "stable" in p.stability_rationale.lower() or "stability" in p.stability_rationale.lower()

    # Verify endpoint GET /matches
    res = client.get("/matches")
    assert res.status_code == 200
    assert "Gale-Shapley Stable Matching" in res.text
    assert "Stable Couples" in res.text

    # Verify API POST /api/matching/stable
    res_api = client.post("/api/matching/stable")
    assert res_api.status_code == 200
    assert "pairs" in res_api.json()


# ---------------------------------------------------------------- 2. Second-Date Planner
def test_second_date_planner_and_intro_drafter():
    client = TestClient(app)
    dates = store.list_dates()
    assert len(dates) > 0
    d = dates[0]
    pa = store.get_person(d.a)
    pb = store.get_person(d.b)

    plan = planner.plan_second_date(d, pa, pb)
    assert plan.date_id == d.id
    assert len(plan.activity) > 0
    assert len(plan.venue_name) > 0
    assert plan.budget_tier in ("$", "$$", "$$$")
    assert len(plan.drafted_intro_for_a) > 0
    assert len(plan.drafted_intro_for_b) > 0

    # Trigger via endpoint
    res = client.post(f"/date/{d.id}/plan", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == f"/date/{d.id}#plan"

    d_saved = store.get_date(d.id)
    assert d_saved.second_date_plan is not None

    # Privacy verification: drafted intro is masked in public view
    res_pub = client.get(f"/date/{d.id}")
    assert res_pub.status_code == 200
    assert "The Second-Date Plan & Human Intro" in html.unescape(res_pub.text)
    assert "[Private drafted message for human]" in res_pub.text
    assert plan.drafted_intro_for_a not in html.unescape(res_pub.text)

    # Authorized view shows the drafted intro
    res_auth = client.get(f"/date/{d.id}?demo_key=test-secret-key-123")
    assert res_auth.status_code == 200
    assert plan.drafted_intro_for_a in html.unescape(res_auth.text)


# ---------------------------------------------------------------- 3. Honesty Judge
def test_honesty_judge_audit():
    client = TestClient(app)
    dates = store.list_dates()
    d = dates[0]
    pa = store.get_person(d.a)
    pb = store.get_person(d.b)

    audit = judge.audit_date(d, pa, pb)
    assert audit.date_id == d.id
    assert 0 <= audit.overall_grounding <= 100
    assert len(audit.audit_summary) > 0
    assert len(audit.verified_claims) >= 1

    # Trigger via endpoint
    res = client.post(f"/date/{d.id}/audit", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == f"/date/{d.id}#audit"

    # Verify rendered in template
    res_page = client.get(f"/date/{d.id}")
    assert res_page.status_code == 200
    assert "Honesty & Grounding Audit" in html.unescape(res_page.text)
    assert "Grounding Score" in res_page.text


# ---------------------------------------------------------------- 4. Multi-Stage Group Hangout
def test_group_hangouts_and_stages():
    client = TestClient(app)
    people = [p for p in store.list_persons() if p.analysis]
    assert len(people) >= 3

    # 1. Test Stage in DateRecord
    d = store.list_dates()[0]
    assert d.stage in ("speed", "dinner", "standard")

    # 2. Run Group Hangout
    top_3 = people[:3]
    gd = group_dater.run_group_hangout(top_3)
    assert gd.id.startswith("grp_")
    assert len(gd.participants) == 3
    assert len(gd.turns) >= 6
    assert gd.group_chemistry > 0
    assert len(gd.social_observations) == 3
    assert len(gd.takeaways) > 0

    store.save_group_date(gd)
    assert store.get_group_date(gd.id) is not None
    assert len(store.list_group_dates()) >= 1

    # 3. View group dates page
    res_list = client.get("/group-dates")
    assert res_list.status_code == 200
    assert "Group Hangouts" in res_list.text
    assert gd.activity in html.unescape(res_list.text)

    # 4. View group date detail
    res_detail = client.get(f"/group-date/{gd.id}")
    assert res_detail.status_code == 200
    assert gd.activity in html.unescape(res_detail.text)
    assert "Social Dynamics & Inclusivity Audit" in res_detail.text

    # 5. API POST /api/group-dates
    res_api = client.post("/api/group-dates", follow_redirects=False)
    assert res_api.status_code == 303
