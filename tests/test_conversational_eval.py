"""Tests for the Conversational Evaluation Research Study.

Verifies:
1. Synthetic personas with hidden ground-truth facts (dealbreakers & concealed aspirations).
2. Evaluation study error metrics: MAE reduction >= 80%, Spearman rho gain, top-match recovery.
3. Publication-quality vector SVG chart rendering.
4. HTTP API endpoints: GET /api/eval/chart.svg and GET /api/eval/conversational-study.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.evaluation.conversational_eval import (
    render_evaluation_comparison_svg,
    run_conversational_study,
)
from app.main import app


def test_conversational_evaluation_study_metrics():
    """Verify conversational dates beat profile-only prior baseline significantly."""
    study = run_conversational_study()

    assert "headline" in study
    assert "metrics" in study
    assert "pairs" in study

    metrics = study["metrics"]
    assert metrics["total_pairs_evaluated"] == 6

    # Verify significant error reduction (>80%)
    assert metrics["error_reduction_pct"] >= 80.0
    assert metrics["mae_agent"] < metrics["mae_prior"]
    assert metrics["rmse_agent"] < metrics["rmse_prior"]

    # Verify rank correlation improvement
    assert metrics["spearman_rho_agent"] >= 0.85
    assert metrics["spearman_rho_gain"] > 1.0

    # Verify true top-1 match was correctly recovered by the agent dates
    assert metrics["agent_recovered_top_match"] is True

    # Verify hidden conversational facts exist in benchmark pairs
    pairs = study["pairs"]
    assert len(pairs) == 6
    for p in pairs:
        assert p["hidden_conversational_facts"] != ""
        assert p["discovery_narrative"] != ""
        assert 0.0 <= p["ground_truth_score"] <= 10.0
        assert 0.0 <= p["baseline_prior_score"] <= 10.0
        assert 0.0 <= p["agent_verdict_score"] <= 10.0


def test_conversational_evaluation_chart_svg():
    """Verify SVG rendering of research comparison chart."""
    study = run_conversational_study()
    svg = render_evaluation_comparison_svg(study)

    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")
    assert "ERROR REDUCTION" in svg
    assert "Ground Truth" in svg
    assert "Profile Prior" in svg
    assert "Agent Date" in svg


def test_conversational_evaluation_endpoints():
    """Verify API endpoints serving the research study and vector SVG."""
    client = TestClient(app)

    # 1. Test GET /api/eval/chart.svg
    res_svg = client.get("/api/eval/chart.svg")
    assert res_svg.status_code == 200
    assert "image/svg+xml" in res_svg.headers.get("content-type", "")
    assert "<svg" in res_svg.text
    assert "ERROR REDUCTION" in res_svg.text

    # 2. Test GET /api/eval/conversational-study
    res_json = client.get("/api/eval/conversational-study")
    assert res_json.status_code == 200
    data = res_json.json()
    assert "headline" in data
    assert "metrics" in data
    assert data["metrics"]["total_pairs_evaluated"] == 6
    assert data["metrics"]["error_reduction_pct"] >= 80.0
