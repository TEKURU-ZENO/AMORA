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
    monkeypatch.setenv("AMORA_DEMO", "1")
    p = harness.ingest_demo(pid, li, ig, progress=lambda m: None)
    assert p.synthetic and p.status == "analyzed" and "example.com" in p.linkedin_url


def test_demo_pool_survives_restart_only_in_demo_mode(monkeypatch):
    monkeypatch.setenv("AMORA_DEMO", "1")
    for pid, li, ig in build()[:3]:
        harness.ingest_demo(pid, li, ig, progress=lambda m: None)
    store.init()
    assert len(store.list_persons()) == 3
    monkeypatch.setenv("AMORA_DEMO", "")
    store.init()  # live mode: fictional personas are purged
    assert store.list_persons() == []


def test_demo_round_runs(monkeypatch):
    monkeypatch.setenv("AMORA_DEMO", "1")
    for pid, li, ig in build()[:6]:
        harness.ingest_demo(pid, li, ig, progress=lambda m: None)
    dates = harness.run_round(progress=lambda m: None)
    assert dates and store.get_meta("rankings")


def test_demo_discovery_uses_fictional_provider_only(monkeypatch):
    monkeypatch.setenv("AMORA_DEMO", "1")
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


def test_new_joiner_dates_the_pool_without_redoing_others(monkeypatch):
    monkeypatch.setenv("AMORA_DEMO", "1")
    from tests.conftest import PERSONAS
    for pid, li, ig in build()[:6]:
        harness.ingest_demo(pid, li, ig, progress=lambda m: None)
    harness.run_round(progress=lambda m: None)
    before = {d.id for d in store.list_dates()}
    _, li, ig = PERSONAS[10]  # a person outside the six, joining through ingest() (stubbed Apify)
    me = harness.ingest(li.url, ig.url, True, progress=lambda m: None)
    assert not me.synthetic
    new = harness.run_round(progress=lambda m: None, only=me.id)
    assert new and all(me.id in (d.a, d.b) for d in new)
    assert {d.id for d in store.list_dates() if me.id not in (d.a, d.b)} == before  # nobody else's dates redone
    assert any(by.synthetic for d in new for by in [store.get_person(d.b if d.a == me.id else d.a)])


def test_buttons_endpoints(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    assert c.post("/api/demo/personas").status_code == 403  # demo mode off
    monkeypatch.setenv("AMORA_DEMO", "1")
    assert "job" in c.post("/api/demo/personas").json()
    assert c.post("/api/people/nobody/date").status_code == 404
