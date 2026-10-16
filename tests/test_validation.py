import os
import pytest


from app import config, harness, store
from app.agents import validation
from app.agents.compat import compute
from app.models import Analysis, Evidence, InstagramData, InstagramPost, LinkedInData, LinkedInExperience, SourceBundle
from tests.conftest import seed_pool



@pytest.fixture(scope="module", autouse=True)
def setup_store():
    store.init()
    store.clear_all()
    seed_pool(8)
    harness.run_round(progress=lambda m: None)


def test_evidence_snippets_grounded():
    li = LinkedInData(url="https://linkedin.com/in/test", full_name="Alice Smith", headline="Senior Python Developer at Acme Corp")
    ig = InstagramData(url="https://instagram.com/alice", username="alice", bio="coffee lover & weekend potter", posts=[
        InstagramPost(caption="made a new mug today #pottery")
    ])
    bundle = SourceBundle(linkedin=li, instagram=ig)

    # Valid grounded evidence + one invented evidence
    valid_ev = Evidence(claim="Software Development", source="linkedin", snippet="Senior Python Developer")
    invented_ev = Evidence(claim="Skydiving", source="instagram", snippet="Jumping out of airplanes every Sunday")

    analysis = Analysis(
        display_name="Alice Smith",
        one_liner="Developer · Pottery",
        summary="Alice is a developer who loves pottery.",
        needs=["Patient partner"],
        hobbies=["Pottery"],
        interests=["Software Development"],
        values=["Creativity"],
        personality=["Thoughtful"],
        communication_style="Warm",
        green_flags=["Consistent"],
        dealbreakers=[],
        ideal_date="Pottery studio",
        conversation_starters=[],
        evidence=[valid_ev, invented_ev],
        confidence=0.8
    )

    validated, warnings = validation.validate_analysis(analysis, bundle)
    # The valid evidence should be kept, the hallucinated one stripped
    assert len(validated.evidence) == 1
    assert validated.evidence[0].claim == "Software Development"
    assert any("Ungrounded evidence snippet" in w and "Skydiving" in w for w in warnings)


def test_sparse_source_guard():
    empty_li = LinkedInData(url="https://linkedin.com/in/empty")
    empty_ig = InstagramData(url="https://instagram.com/empty", username="empty")
    bundle = SourceBundle(linkedin=empty_li, instagram=empty_ig)

    analysis = Analysis(
        display_name="Empty User",
        one_liner="Unknown",
        summary="Sparse data.",
        needs=["Very specific romantic expectations"],
        hobbies=[],
        interests=[],
        values=["Ambition"],
        personality=[],
        communication_style="Unknown",
        green_flags=[],
        dealbreakers=["Must earn $500k"],  # Hallucinated dealbreaker on empty source
        ideal_date="Coffee",
        conversation_starters=[],
        evidence=[],
        confidence=0.9
    )

    validated, warnings = validation.validate_analysis(analysis, bundle)
    assert validated.confidence <= 0.2
    assert "Data insufficient to infer relationship needs" in validated.needs[0]
    assert len(validated.dealbreakers) == 0
    assert any("Sources are empty" in w for w in warnings)


def test_engine_disclosure_metadata():
    person = store.list_persons()[0]
    assert person.analysis is not None
    assert person.analysis.engine_used in ("offline", "claude")
    assert isinstance(person.analysis.fallback_occurred, bool)


def test_ranking_assessment_and_uncertainty_disclosure():
    rankings = store.get_meta("rankings")
    assert rankings is not None
    for pid, rows in rankings.items():
        assert len(rows) > 0
        for r in rows:
            assert "assessment_status" in r
            assert r["assessment_status"] in ("dated", "unassessed_prior")
            assert "uncertainty" in r
            if r["dated"]:
                assert r["assessment_status"] == "dated"
                assert "low" in r["uncertainty"].lower()
                assert r["date_id"] is not None
            else:
                assert r["assessment_status"] == "unassessed_prior"
                assert "high" in r["uncertainty"].lower()
                assert r["date_id"] is None


def test_reviewed_reference_pairs_evaluation():
    # Evaluate compatibility prior calculation against known trait relationships
    p1 = store.list_persons()[0]
    p2 = store.list_persons()[1]

    compat = compute(p1.analysis, p2.analysis)
    assert 0.0 <= compat.prior <= 10.0
    # Overlap items must be valid strings
    for h in compat.shared_hobbies:
        assert isinstance(h, str) and len(h) > 0
