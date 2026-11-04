"""Test suite for the 3 new major features:
1. Shareable Story Card Generator (9:16 Instagram Story)
2. Evaluation Harness with Precision@K, NDCG, MRR, and Prompt Caching Economics
3. Live SSE Date Streaming with Turn-by-Turn Mood & Typing Indicators
"""
import html
import json
import pytest
from starlette.testclient import TestClient

from app import harness, store
from app.agents import dater
from app.evaluation import benchmark, metrics, synthetic_couples
from app.main import app
from app.models import Turn
from app.story_card import build_story_card_data, render_story_card_svg
from tests.conftest import seed_pool


@pytest.fixture(scope="module", autouse=True)
def setup_test_suite():
    store.init()
    store.clear_all()
    seed_pool(8)
    harness.run_round(progress=lambda m: None)


# =====================================================================
# Feature 1: Shareable Story Card Generator (9:16 Instagram Story)
# =====================================================================

def test_build_story_card_data():
    client = TestClient(app)
    persons = [p for p in store.list_persons() if p.analysis]
    assert len(persons) >= 2, "Need at least 2 analyzed persons for tests"
    p = persons[0]

    data = build_story_card_data(p.id)
    assert data["person_id"] == p.id
    assert data["name"] == p.analysis.display_name
    assert len(data["initials"]) >= 1
    assert data["dates_count"] >= 1
    assert data["hours_saved"] >= 4
    assert data["match_name"]
    assert data["match_score"] > 0
    assert data["quote"]
    assert len(data["chips"]) >= 1
    assert data["honesty_score"] >= 80.0


def test_render_story_card_svg():
    persons = [p for p in store.list_persons() if p.analysis]
    p = persons[0]
    data = build_story_card_data(p.id)
    svg = render_story_card_svg(data)

    assert "<svg" in svg
    assert 'viewBox="0 0 1080 1920"' in svg
    assert "AMORA DISPATCH" in svg
    assert "My AI agent went on" in svg
    assert "dates this week." in svg
    assert data["match_name"] in svg
    assert f"{data['match_score']:.1f}" in svg
    assert "HOURS SAVED" in svg
    assert "</svg>" in svg


def test_story_card_endpoints():
    client = TestClient(app)
    persons = [p for p in store.list_persons() if p.analysis]
    pid = persons[0].id

    # 1. HTML view
    res_html = client.get(f"/person/{pid}/story-card")
    assert res_html.status_code == 200
    assert "Instagram Story" in res_html.text
    assert "Download Story PNG" in res_html.text

    # 2. Raw SVG view
    res_svg = client.get(f"/api/people/{pid}/story-card.svg")
    assert res_svg.status_code == 200
    assert res_svg.headers["content-type"].startswith("image/svg+xml")
    assert "<svg" in res_svg.text

    # 3. JSON Data API
    res_data = client.get(f"/api/people/{pid}/story-data")
    assert res_data.status_code == 200
    j = res_data.json()
    assert j["person_id"] == pid
    assert "match_score" in j


# =====================================================================
# Feature 2: Evaluation Harness & IR Benchmarks
# =====================================================================

def test_synthetic_couples_testbed():
    people, couples = synthetic_couples.generate_benchmark_testbed()
    assert len(people) == 12
    assert len(couples) >= 6

    categories = {c.category for c in couples}
    assert "compatible" in categories
    assert "dealbreaker_clash" in categories
    assert "superficial_trap" in categories


def test_ir_metrics_calculations():
    # Precision@K and Recall@K
    ranked = ["item_a", "item_b", "item_c", "item_d", "item_e"]
    relevant = {"item_a", "item_c"}

    p1 = metrics.precision_at_k(ranked, relevant, k=1)
    assert p1 == 1.0  # item_a is relevant

    p3 = metrics.precision_at_k(ranked, relevant, k=3)
    assert p3 == 1.0  # both recovered in top 3 (2 / min(3, 2) = 1.0)

    r3 = metrics.recall_at_k(ranked, relevant, k=3)
    assert r3 == 1.0  # both recovered in top 3

    # Reciprocal Rank
    rr = metrics.reciprocal_rank(ranked, relevant)
    assert rr == 1.0

    # NDCG@K
    weights = {"item_a": 3.0, "item_b": 0.0, "item_c": 2.0}
    ndcg = metrics.ndcg_at_k(ranked, weights, k=3)
    assert 0.8 <= ndcg <= 1.0

    # Kendall's Tau Stability
    tau_identical = metrics.compute_kendall_tau(["a", "b", "c"], ["a", "b", "c"])
    assert tau_identical == 1.0

    tau_reversed = metrics.compute_kendall_tau(["a", "b", "c"], ["c", "b", "a"])
    assert tau_reversed == -1.0

    # Prompt Caching Economics
    econ = metrics.calculate_prompt_caching_economics(total_dates=10, turns_per_date=10)
    assert econ["total_calls"] == 100
    assert econ["uncached_total_cost_usd"] > econ["cached_total_cost_usd"]
    assert econ["percentage_cost_reduction"] >= 40.0
    assert econ["cache_hit_rate_pct"] >= 80.0


def test_run_evaluation_benchmark():
    result = benchmark.run_evaluation_benchmark(run_stability_check=True)

    assert result.summary.total_couples_audited >= 6
    assert result.summary.precision_at_1 >= 0.8
    assert result.summary.precision_at_3 >= 0.8
    assert result.summary.ndcg_at_3 >= 0.8
    assert result.summary.dealbreaker_detection_rate >= 0.8
    assert result.summary.superficial_trap_rejection_rate >= 0.8
    assert result.summary.stability_tau >= 0.8
    assert result.summary.overall_pass_rate_pct >= 80.0
    assert result.caching_economics["percentage_cost_reduction"] >= 40.0

    # Check that individual audits contain compatible, dealbreaker, and trap entries
    categories = {a.category for a in result.audits}
    assert "compatible" in categories
    assert "dealbreaker_clash" in categories
    assert "superficial_trap" in categories


def test_benchmark_endpoints():
    client = TestClient(app)

    # 1. HTML Dashboard
    res = client.get("/benchmark")
    assert res.status_code == 200
    assert "Evaluation Harness" in res.text
    assert "Prompt Caching &amp; Token Economics" in res.text or "Prompt Caching & Token Economics" in res.text
    assert "Ground Truth Verification Matrix" in res.text

    # 2. JSON API Run
    res_api = client.post("/api/eval/run", headers={"Accept": "application/json"})
    assert res_api.status_code == 200
    j = res_api.json()
    assert "summary" in j
    assert j["summary"]["precision_at_1"] >= 0.8

    # 3. Latest Benchmark API
    res_latest = client.get("/api/eval/latest")
    assert res_latest.status_code == 200
    j2 = res_latest.json()
    assert "caching_economics" in j2


# =====================================================================
# Feature 3: Live SSE Date Streaming & Mood Indicators
# =====================================================================

def test_infer_turn_mood():
    t_spark = Turn(speaker="a", text="I had so much fun, there is real chemistry!", thought="Clicking fast")
    assert dater.infer_turn_mood(t_spark) == "spark"

    t_db = Turn(speaker="a", text="That's a red flag for me, dealbreaker.", thought="Boundary alert")
    assert dater.infer_turn_mood(t_db) == "dealbreaker_check"

    t_probe = Turn(speaker="a", text="What do you actually need from a relationship?", thought="Probing depth")
    assert dater.infer_turn_mood(t_probe) == "probing"

    t_vuln = Turn(speaker="a", text="Honestly, I've learned that the hard way.", thought="Sharing real truth")
    assert dater.infer_turn_mood(t_vuln) == "vulnerable"

    t_play = Turn(speaker="a", text="Ha, you did your homework! Fair warning, I might tease you.", thought="Teasing")
    assert dater.infer_turn_mood(t_play) == "playful"


def test_go_on_date_with_turn_callback():
    persons = [p for p in store.list_persons() if p.analysis]
    pa, pb = persons[0], persons[1]

    captured_turns = []

    def on_turn_cb(t, idx, total):
        captured_turns.append((t, idx, total))

    date_rec = dater.go_on_date(pa.id, pa.analysis, pb.id, pb.analysis, on_turn=on_turn_cb)

    assert len(captured_turns) == len(date_rec.turns)
    assert len(captured_turns) >= 4
    for t, idx, total in captured_turns:
        assert t.mood in ["spark", "probing", "dealbreaker_check", "vulnerable", "playful", "thoughtful", "open"]


def test_live_date_stream_sse_endpoint():
    client = TestClient(app)
    dates = store.list_dates()
    assert dates, "Need at least one date in store"
    did = dates[0].id

    # Test SSE Streaming endpoint
    with client.stream("GET", f"/api/dates/{did}/stream?speed=10.0") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                data_str = line[len("data: "):]
                events.append(json.loads(data_str))

        # Check event types received
        event_types = [e.get("event") for e in events if "event" in e]
        assert "start" in event_types
        assert "typing" in event_types
        assert "turn" in event_types
        assert "verdicts" in event_types
        assert any(e.get("done") for e in events)

        # Check turn details
        turn_events = [e for e in events if e.get("event") == "turn"]
        assert len(turn_events) > 0
        first_turn = turn_events[0]
        assert "speaker" in first_turn
        assert "text" in first_turn
        assert "mood" in first_turn
