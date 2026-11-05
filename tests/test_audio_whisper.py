"""Tests for Voice Date Podcast Cues, Server-side Audio, and Mid-Date Whisper Injection."""
import pytest
from starlette.testclient import TestClient

from app import harness, store
from app.audio import podcast
from app.main import app
from tests.conftest import seed_pool


@pytest.fixture(scope="module", autouse=True)
def setup_test_suite():
    store.init()
    store.clear_all()
    seed_pool(6)
    harness.run_round(progress=lambda m: None)


def test_audio_cues_generation():
    """Verify audio cues are built with dual-voice pitches, moods, and timestamps."""
    dates = store.list_dates()
    assert len(dates) >= 1
    d = dates[0]
    pa = store.get_person(d.a)
    pb = store.get_person(d.b)

    cues = podcast.build_audio_cues(d, pa, pb, authorized=True)
    assert len(cues) >= len(d.turns) + 1  # intro cue + turns

    # Check intro cue
    intro = cues[0]
    assert intro["speaker_id"] == "narrator"
    assert "Welcome to the date replay" in intro["text"]

    # Check conversation turns
    for cue in cues[1:]:
        assert cue["turn_index"] >= 0
        assert cue["speaker_id"] in (d.a, d.b)
        assert cue["speaker_name"] != ""
        assert cue["duration_sec"] > 0
        assert "voice_settings" in cue
        assert "pitch" in cue["voice_settings"]
        assert "tld" in cue["voice_settings"]


def test_audio_cues_api_endpoint():
    """Verify GET /api/dates/{did}/audio-cues HTTP endpoint."""
    client = TestClient(app)
    dates = store.list_dates()
    d = dates[0]

    res = client.get(f"/api/dates/{d.id}/audio-cues")
    assert res.status_code == 200
    cues = res.json()
    assert isinstance(cues, list)
    assert len(cues) >= 2


def test_mid_date_whisper_security():
    """Verify POST /api/dates/{did}/whisper requires valid persona authority."""
    client = TestClient(app)
    dates = store.list_dates()
    d = dates[0]
    pa = store.get_person(d.a)

    # 1. Unauthenticated request without token must fail with 403 Forbidden
    res_unauth = client.post(
        f"/api/dates/{d.id}/whisper",
        data={"pid": d.a, "whisper": "Ask about their travel plans!"},
    )
    assert res_unauth.status_code == 403
    assert "Forbidden" in res_unauth.json().get("detail", "")

    # 2. Request with invalid token must fail with 403 Forbidden
    res_bad = client.post(
        f"/api/dates/{d.id}/whisper",
        data={"pid": d.a, "whisper": "Ask about their travel plans!", "token": "invalid-token-1234"},
    )
    assert res_bad.status_code == 403

    # 3. Request with valid edit_token must succeed with 200 OK
    res_ok = client.post(
        f"/api/dates/{d.id}/whisper",
        data={"pid": d.a, "whisper": "Ask about their travel plans!", "token": pa.edit_token},
    )
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert data["status"] == "delivered"
    assert data["speaker"] == d.a
    assert data["whisper"] == "Ask about their travel plans!"

    # 4. Verify whisper is persisted on date record
    d_updated = store.get_date(d.id)
    assert len(d_updated.whispers) >= 1
    assert any(w["whisper"] == "Ask about their travel plans!" for w in d_updated.whispers)
