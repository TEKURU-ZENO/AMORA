import pytest
from fastapi.testclient import TestClient

from app import discovery, store
from app.main import app
from tests.conftest import CALLS


@pytest.fixture(scope="module", autouse=True)
def setup_store():
    store.init()
    store.clear_all()
    discovery.registry.init()
    discovery.orchestrator.run_discovery_batch(query="designer", limit=6)


def by_handle(part):
    return [c for c in discovery.registry.list_candidates() if part in c.linkedin_handle]


def test_discovery_uses_apify_search_only():
    queries = [q for kind, q in CALLS if kind == "search"]
    assert "site:linkedin.com/in/ designer" in queries
    # every candidate is a real LinkedIn profile URL from the search; company pages are dropped
    regs = discovery.registry.list_candidates()
    assert len(regs) == 5 and all("/in/" in c.linkedin_url for c in regs)


def test_strict_crosslink_verification():
    maya = by_handle("maya")[0]  # Instagram found by name search; its bio link points at her LinkedIn
    assert maya.status == "verified_crosslink" and maya.verification_method == "direct_crosslink"
    assert maya.invitation_token and maya.invitation_token.startswith("inv_")
    liam = by_handle("liam")[0]  # handle mentioned on LinkedIn; bio links back
    assert liam.status == "verified_crosslink"


def test_ambiguous_candidate_requires_human_verification():
    elena = by_handle("elena")[0]  # name match, no cross-link
    assert elena.status == "requires_human_verification"
    assert "no direct cross-link" in elena.rejection_reason.lower()
    assert elena.invitation_token is None


def test_private_and_unpaired():
    zoe = by_handle("zoe")[0]
    assert zoe.status == "rejected" and "private" in zoe.rejection_reason.lower()
    omar = by_handle("omar")[0]  # no handle mentioned and no Instagram result for the name
    assert omar.status == "pairing_failed"


def test_human_review_workflow():
    client = TestClient(app)
    elena = by_handle("elena")[0]
    res = client.post(f"/api/discovery/candidates/{elena.id}/review", data={"action": "approve"}, follow_redirects=False)
    assert res.status_code == 303
    updated = discovery.registry.get_candidate(elena.id)
    assert updated.status == "verified_crosslink" and updated.verification_method == "human_review"
    assert updated.invitation_token is not None


def test_discovery_pages_and_invite_flow(monkeypatch):
    client = TestClient(app)
    assert "Candidate Registry" in client.get("/discovery").text
    maya = by_handle("maya")[0]
    join = client.get(f"/join?token={maya.invitation_token}")
    assert join.status_code == 200 and "Verified Candidate Invitation" in join.text and maya.linkedin_url in join.text
    # the search endpoint runs as a background job and redirects to its live log
    res = client.post("/api/discovery/search", data={"query": "chef", "limit": 2}, follow_redirects=False)
    assert res.status_code == 303 and res.headers["location"].startswith("/discovery?job=")
    monkeypatch.setenv("APIFY_TOKEN", "")
    assert client.post("/api/discovery/search", data={"query": "x"}).status_code == 503
