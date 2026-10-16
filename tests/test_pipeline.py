import os
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp()
os.environ["ANTHROPIC_API_KEY"] = ""  # set empty so a local .env cannot switch engines on
os.environ["APIFY_TOKEN"] = ""

import pytest
from fastapi.testclient import TestClient

from app import harness, store
from app.main import app
from app.scrape.apify import _norm_instagram, _norm_linkedin
from app.scrape.links import LinkError, normalize_instagram, normalize_linkedin
from scripts.synthetic import build


@pytest.fixture(scope="module", autouse=True)
def seeded():
    store.init()
    for pid, li, ig in build():
        harness.ingest_sources(pid, li, ig, synthetic=True, progress=lambda m: None)
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


def test_pages_and_guards():
    c = TestClient(app)
    p = store.list_persons()[0]
    d = store.list_dates()[0]
    for u in ["/", "/join", "/round", "/dates", "/rankings", "/how", f"/person/{p.id}", f"/date/{d.id}", "/api/export"]:
        assert c.get(u).status_code == 200, u
    r = c.post("/api/people", data={"linkedin": "https://www.linkedin.com/in/a-b", "instagram": "https://instagram.com/ab"})
    assert r.status_code == 400  # no consent
    r = c.post("/api/people", data={"linkedin": "https://www.linkedin.com/in/a-b", "instagram": "https://instagram.com/ab", "consent": "yes"})
    assert r.status_code == 503  # no Apify token in tests
    assert c.post(f"/person/{p.id}/delete", follow_redirects=False).status_code == 303
    assert store.get_person(p.id) is None and not store.list_dates(p.id)
