import os
import pytest


from app import config, harness, store
from app.models import InstagramData, LinkedInData, Person, SourceBundle



@pytest.fixture(scope="module", autouse=True)
def setup_store():
    store.init()
    store.clear_all()



def test_job_persistence_and_logging():
    job_id = "test_job_123"
    job, is_new = store.create_or_get_job(
        job_id=job_id,
        job_type="ingest",
        idempotency_key="ingest:test-key-1",
        entity_id="person_1"
    )
    assert is_new is True
    assert job["id"] == job_id
    assert job["status"] == "queued"

    # Append logs
    store.append_job_log(job_id, "Step 1: Scraping started")
    store.append_job_log(job_id, {"type": "progress", "percent": 50})

    # Update status and checkpoint
    store.update_job(job_id, status="running", stage="scraped_li", stage_data={"scraped_items": 10})

    # Read back from SQLite
    persisted = store.get_job(job_id)
    assert persisted is not None
    assert persisted["status"] == "running"
    assert persisted["stage"] == "scraped_li"
    assert persisted["stage_data"] == {"scraped_items": 10}

    logs = store.get_job_logs(job_id)
    assert len(logs) == 2
    assert logs[0] == "Step 1: Scraping started"
    assert logs[1] == {"type": "progress", "percent": 50}


def test_job_idempotency():
    # Calling create_or_get_job with the same idempotency key must return the existing job
    job, is_new = store.create_or_get_job(
        job_id="test_job_duplicate",
        job_type="ingest",
        idempotency_key="ingest:test-key-1"  # Same key as previous test
    )
    assert is_new is False
    assert job["id"] == "test_job_123"


def test_server_restart_recovery():
    # Simulate a job running when the process crashes
    crash_job_id = "crashed_job_999"
    store.create_or_get_job(
        job_id=crash_job_id,
        job_type="round",
        idempotency_key="round:test-crash",
        stage="dating"
    )
    store.update_job(crash_job_id, status="running", stage="dating", stage_data={"completed_dates": 4})

    # Simulate process restart by calling recover_interrupted_jobs()
    recovered = store.recover_interrupted_jobs()
    assert crash_job_id in recovered

    job = store.get_job(crash_job_id)
    assert job["status"] == "failed"
    assert "interrupted" in job["error"].lower()
    # Checkpoint data preserved
    assert job["stage_data"] == {"completed_dates": 4}


def test_ingestion_checkpoint_resumption():
    from app.scrape.links import normalize_linkedin, normalize_instagram, person_id
    li_url, li_h = normalize_linkedin("https://www.linkedin.com/in/resumption-test")
    ig_url, ig_h = normalize_instagram("https://instagram.com/resumption_test")
    pid = person_id(li_h, ig_h)
    li = LinkedInData(url=li_url, full_name="Resumption Test", headline="Engineer")
    ig = InstagramData(url=ig_url, username=ig_h, bio="Test bio")
    
    # Save person with sources
    p = Person(id=pid, linkedin_url=li.url, instagram_url=ig.url, consent=True, sources=SourceBundle(linkedin=li, instagram=ig), status="scraped")
    store.save_person(p)


    events = []
    # Call ingest - should reuse checkpoint without error even without APIFY_TOKEN
    analyzed = harness.ingest(
        linkedin_url="https://www.linkedin.com/in/resumption-test",
        instagram_url="https://instagram.com/resumption_test",
        consent=True,
        progress=lambda msg: events.append(msg)
    )

    assert analyzed.status == "analyzed"
    assert analyzed.analysis is not None
    assert any("using existing scraped sources from checkpoint" in str(e) for e in events)
