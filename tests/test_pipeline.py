import json

import pytest
from fastapi.testclient import TestClient

from app import harness, store
from app.scrape import apify
from app.main import app
from app.scrape.apify import _norm_instagram, _norm_linkedin
from app.scrape.links import LinkError, normalize_instagram, normalize_linkedin
from tests.conftest import CALLS, INSTAGRAM, LINKEDIN, seed_pool


@pytest.fixture(scope="module", autouse=True)
def seeded():
    store.init()
    store.clear_all()
    seed_pool(25)
    harness.run_round(progress=lambda m: None)



def test_links():
    assert normalize_linkedin("https://in.linkedin.com/in/jane-doe-12/")[1] == "jane-doe-12"
    assert normalize_instagram("https://instagram.com/jane.doe")[1] == "jane.doe"
    for bad in ["https://www.linkedin.com/company/acme", "https://x.com/jane"]:
        with pytest.raises(LinkError):
            normalize_linkedin(bad)
    with pytest.raises(LinkError):
        normalize_instagram("https://www.instagram.com/p/Cxyz/")


def test_apify_normalizers():
    ig = _norm_instagram("u", {"username": "j", "biography": "hi", "private": False, "followersCount": 10,
                               "latestPosts": [{"caption": "trail day #hiking", "type": "Image"}]})
    assert ig.posts[0].hashtags == ["hiking"] and not ig.is_private
    # some actor versions only return the bio links as a list
    ig = _norm_instagram("u", {"username": "j", "externalUrls": [{"title": "", "url": "https://linkedin.com/in/j"}]})
    assert ig.external_url == "https://linkedin.com/in/j"
    li = _norm_linkedin("u", {"fullName": "Jane", "headline": "Eng", "experiences": [{"title": "Eng", "subtitle": "Acme"}],
                              "skills": [{"title": "Python"}], "educations": [{"title": "IIT"}]})
    assert li.experience[0].company == "Acme" and li.skills == ["Python"] and li.education == ["IIT"]


def test_every_person_analyzed_with_evidence():
    ps = store.list_persons()
    assert len(ps) == 25
    for p in ps:
        assert p.status == "analyzed" and p.analysis.needs and p.analysis.hobbies
        assert all(e.source in ("linkedin", "instagram") for e in p.analysis.evidence)


def test_dates_and_rankings():
    ds = store.list_dates()
    assert ds and all(len(d.turns) >= 8 for d in ds)
    r = store.get_meta("rankings")
    assert set(r) == {p.id for p in store.list_persons()}
    for rows in r.values():
        assert len(rows) == 24 and rows == sorted(rows, key=lambda x: (-x["fit"], x["id"]))
    assert all(any(row["dated"] for row in rows) for rows in r.values())


def test_pool_is_built_through_apify():
    # every person came in through ingest(): one LinkedIn and one Instagram scrape each
    ps = store.list_persons()
    scraped_li = {u for kind, u in CALLS if kind == "linkedin"}
    scraped_ig = {h for kind, h in CALLS if kind == "instagram"}
    for p in ps:
        assert p.linkedin_url in scraped_li and p.sources.instagram.username in scraped_ig


def test_pages_and_guards(monkeypatch):
    c = TestClient(app)
    p = store.list_persons()[0]
    d = store.list_dates()[0]
    for u in ["/", "/join", "/round", "/dates", "/rankings", "/how", f"/person/{p.id}", f"/date/{d.id}", "/api/export"]:
        assert c.get(u).status_code == 200, u
    r = c.post("/api/people", data={"linkedin": "https://www.linkedin.com/in/a-b", "instagram": "https://instagram.com/ab"})
    assert r.status_code == 400  # no consent
    monkeypatch.setenv("APIFY_TOKEN", "")
    r = c.post("/api/people", data={"linkedin": "https://www.linkedin.com/in/a-b", "instagram": "https://instagram.com/ab", "consent": "yes"})
    assert r.status_code == 503  # Apify-only: without a token nobody can join
    assert c.post(f"/person/{p.id}/delete", follow_redirects=False).status_code == 303
    assert store.get_person(p.id) is None and not store.list_dates(p.id)


def test_partial_and_private_instagram(monkeypatch):
    li = next(iter(LINKEDIN.values()))
    # Instagram scrape fails: profile is still built from LinkedIn, with a warning
    store.delete_person(harness.person_id(li.url.split("/in/")[1].strip("/"), "x"))
    p = harness.ingest(li.url, "https://www.instagram.com/nobody_here/", True, progress=lambda m: None)
    assert p.status == "analyzed" and any("Instagram could not be read" in w for w in p.warnings)
    # a private Instagram stops the read entirely
    store.delete_person(p.id)
    private = next(iter(INSTAGRAM.values())).model_copy(update={"is_private": True})
    monkeypatch.setattr(apify, "fetch_instagram", lambda url, h, posts=24: private)
    with pytest.raises(apify.PrivateProfile):
        harness.ingest(li.url, "https://www.instagram.com/someone/", True, progress=lambda m: None)
    assert store.get_person(p.id).status == "error"


def test_second_round_and_rejoin_are_not_blocked():
    # regression: finished jobs used to be reused forever by their idempotency key
    first, new = store.create_or_get_job("r1", "round", idempotency_key="round:active")
    store.update_job("r1", status="succeeded")
    second, is_new = store.create_or_get_job("r2", "round", idempotency_key="round:active")
    assert is_new and second["id"] == "r2"


def test_synthetic_rows_are_purged():
    p = store.list_persons()[0]
    body = json.loads(p.model_dump_json()) | {"synthetic": True}
    with store._conn() as c:
        c.execute("INSERT OR REPLACE INTO persons VALUES (?, ?)", ("fake-person", json.dumps(body | {"id": "fake-person"})))
    assert store.purge_synthetic() == 1 and store.get_person("fake-person") is None
