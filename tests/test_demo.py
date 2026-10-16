import pytest

from app import discovery, harness, store
from app.scrape import apify
from scripts.synthetic import build
from tests.conftest import CALLS


@pytest.fixture(autouse=True)
def fresh():
    store.init()
    store.clear_all()
    discovery.registry.init()


def test_demo_personas_need_demo_mode(monkeypatch):
    pid, li, ig = build()[0]
    with pytest.raises(ValueError):
        harness.ingest_demo(pid, li, ig, progress=lambda m: None)
    monkeypatch.setenv("AGENTDATE_DEMO", "1")
    p = harness.ingest_demo(pid, li, ig, progress=lambda m: None)
    assert p.synthetic and p.status == "analyzed" and "example.com" in p.linkedin_url


def test_demo_pool_survives_restart_only_in_demo_mode(monkeypatch):
    monkeypatch.setenv("AGENTDATE_DEMO", "1")
    for pid, li, ig in build()[:3]:
        harness.ingest_demo(pid, li, ig, progress=lambda m: None)
    store.init()
    assert len(store.list_persons()) == 3
    monkeypatch.setenv("AGENTDATE_DEMO", "")
    store.init()  # live mode: fictional personas are purged
    assert store.list_persons() == []


def test_demo_round_runs(monkeypatch):
    monkeypatch.setenv("AGENTDATE_DEMO", "1")
    for pid, li, ig in build()[:6]:
        harness.ingest_demo(pid, li, ig, progress=lambda m: None)
    dates = harness.run_round(progress=lambda m: None)
    assert dates and store.get_meta("rankings")


def test_demo_discovery_uses_fictional_provider_only(monkeypatch):
    monkeypatch.setenv("AGENTDATE_DEMO", "1")
    monkeypatch.setenv("APIFY_TOKEN", "")  # demo discovery must not need, or touch, Apify
    before = len(CALLS)
    monkeypatch.setattr(apify, "google_search", lambda *a, **k: pytest.fail("live search called in demo mode"))
    cands = discovery.orchestrator.run_discovery_batch(query="", limit=6)
    assert len(CALLS) == before
    status = {c.linkedin_handle: c.status for c in cands}
    assert status == {
        "maya-patel-demo": "verified_crosslink",       # bio link points at the LinkedIn profile
        "liam-chen-demo": "verified_crosslink",        # handle mentioned on LinkedIn, bio links back
        "elena-rostova-demo": "requires_human_verification",
        "zoe-alvarez-demo": "rejected",                # private
        "aravind-nair-demo": "verified_crosslink",
        "omar-haddad-demo": "pairing_failed",          # no Instagram found
    }
