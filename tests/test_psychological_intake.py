"""Tests for AMORA Psychological & Behavioral Archetype Profiling Engine.

Verifies:
1. 12 Canonical Relational Archetypes & Stereotypes.
2. Attachment dynamic and conflict resolution inference.
3. Life, Work, and Future dimensions synthesis.
4. Compliance-first, zero web scraping guarantees with direct evidence receipts.
5. HTTP Endpoints: GET /intake and POST /api/intake/psychological.
6. Autonomous dating agents matching the persona's psychological archetype.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import store
from app.agents import dater
from app.intake import (
    ARCHETYPES,
    ATTACHMENT_STYLES,
    CONFLICT_STYLES,
    classify_archetype,
    infer_attachment_style,
    infer_conflict_style,
    synthesize_psychological_persona,
)
from app.main import app


def test_archetypes_and_dimensions_definitions():
    """Verify 12 canonical archetypes and psychological dimensions are defined."""
    assert len(ARCHETYPES) == 12
    assert "contemplative_craftsman" in ARCHETYPES
    assert "visionary_builder" in ARCHETYPES
    assert "grounded_sanctuary" in ARCHETYPES
    assert "mindful_nomad" in ARCHETYPES
    assert "high_velocity_strategist" in ARCHETYPES
    assert "empathic_healer" in ARCHETYPES
    assert "cozy_domesticist" in ARCHETYPES
    assert "high_octane_catalyst" in ARCHETYPES
    assert "intentional_minimalist" in ARCHETYPES
    assert "sensual_epicurean" in ARCHETYPES
    assert "holistic_seeker" in ARCHETYPES
    assert "playful_maverick" in ARCHETYPES

    for aid, arch in ARCHETYPES.items():
        assert arch["id"] == aid
        assert arch["name"] != ""
        assert len(arch["traits"]) >= 3
        assert len(arch["keywords"]) >= 5
        assert arch["dating_strengths"] != ""

    assert len(ATTACHMENT_STYLES) == 4
    assert "secure" in ATTACHMENT_STYLES
    assert "anxious" in ATTACHMENT_STYLES
    assert "avoidant" in ATTACHMENT_STYLES
    assert "fearful" in ATTACHMENT_STYLES

    assert len(CONFLICT_STYLES) == 4
    assert "collaborative" in CONFLICT_STYLES
    assert "processing_space" in CONFLICT_STYLES
    assert "high_candor" in CONFLICT_STYLES


def test_archetype_and_behavioral_classification():
    """Verify classifier maps behavioral text to accurate archetypes and attachment dynamics."""
    # 1. Craftsman
    name, traits = classify_archetype("Quiet woodcraft, comfortable silence, modular synthesis, slow focus")
    assert "Craftsman" in name
    assert len(traits) >= 3

    # 2. Builder
    name, traits = classify_archetype("Building an AI startup, founder velocity, scaling tech products")
    assert "Builder" in name

    # 3. Nomad
    name, traits = classify_archetype("Backpacking across continents, perpetual travel, digital nomad life")
    assert "Nomad" in name

    # 4. Attachment inference
    assert infer_attachment_style("I am comfortable with closeness, but value personal independence") == "Secure"
    assert infer_attachment_style("I need 30 minutes of space to de-escalate and self-reliantly process") == "Dismissive-Avoidant"
    assert infer_attachment_style("I get anxious and overthink when communication is silent or ambiguous") == "Anxious-Preoccupied"

    # 5. Conflict style inference
    assert infer_conflict_style("I need 30 minutes of space to cool down before talking") == "Regulated Processing (Space First)"
    assert infer_conflict_style("I want immediate raw candor and direct truth straight away") == "High-Candor Directness"
    assert infer_conflict_style("I listen calmly and validate how they feel before working on solutions") == "Collaborative & Validating"


def test_synthesize_psychological_persona_zero_scraping():
    """Verify complete persona synthesis without scraping, with grounded evidence and archetype brief."""
    answers = {
        "archetype_preference": "contemplative_craftsman",
        "sunday_rhythm": "Quiet pour-over coffee, morning light, trail running, then parallel creative bookbinding in comfortable silence.",
        "geo_anchor": "Rooted permanently in this city caring for family; non-negotiable anchor.",
        "family_vision": "Want 2 kids in a grounded nature-connected home within 3 years.",
        "social_battery": "Low-drain introvert battery; recharges through quiet domestic weekends.",
        "work_ambition": "Deep focus craftsmanship; strict 5 PM boundary for evening personal connection.",
        "financial_philosophy": "Intentional minimalism and FIRE savings; anti-conspicuous consumption.",
        "future_vision": "Secretly planning to open a community craft binding studio and rural clinic.",
        "attachment_choice": "secure",
        "conflict_choice": "collaborative",
        "dealbreakers": "Relocating abroad, heavy smoking, aggressive sarcastic mockery, workaholism on dates.",
        "ideal_date": "A quiet corner at an intimate vinyl cafe with warm tea and ambient acoustics.",
    }

    person = synthesize_psychological_persona(
        display_name="Devan Nair",
        one_liner="Restoration Bookbinder & Classical Acoustician",
        answers=answers,
        pid="test-psych-user-1",
    )

    assert person.id == "test-psych-user-1"
    assert person.status == "analyzed"
    assert person.consent is True

    # Analysis verification
    analysis = person.analysis
    assert analysis is not None
    assert analysis.archetype == "The Contemplative Craftsman"
    assert len(analysis.archetype_traits) >= 3
    assert analysis.attachment_style == "Secure"
    assert analysis.conflict_style == "Collaborative & Validating"
    assert analysis.future_horizon == answers["future_vision"]
    assert "mobility" in analysis.life_architecture
    assert "ambition_pace" in analysis.work_ethos
    assert len(analysis.psychological_patterns) >= 4
    assert len(analysis.needs) >= 3
    assert len(analysis.dealbreakers) >= 2

    # Evidence receipts citing user's direct responses (Zero Scraping)
    assert len(analysis.evidence) >= 4
    for ev in analysis.evidence:
        assert ev.source == "psychological_intake"
        assert ev.claim != ""
        assert ev.snippet != ""

    # Coaching directives instructing the autonomous dating agent
    assert len(person.coaching_notes) >= 3
    assert any("The Contemplative Craftsman" in note for note in person.coaching_notes)
    assert any("Secure" in note for note in person.coaching_notes)


def test_psychological_intake_http_endpoints():
    """Verify HTTP API endpoints for psychological assessment."""
    client = TestClient(app)

    # 1. GET /intake renders psychological assessment portal
    res_get = client.get("/intake")
    assert res_get.status_code == 200
    assert "Psychological &amp; Behavioral Dating Assessment" in res_get.text or "Psychological & Behavioral Dating Assessment" in res_get.text
    assert "1. Identity &amp; Relational Archetype" in res_get.text or "1. Identity & Relational Archetype" in res_get.text
    assert "ZERO WEB SCRAPING" in res_get.text
    assert "The Contemplative Craftsman" in res_get.text

    # 2. GET /join renders zero-scraping onboarding
    res_join = client.get("/join")
    assert res_join.status_code == 200
    assert "Zero Scraping Guarantee" in res_join.text
    assert "Start Psychological Assessment" in res_join.text

    # 3. POST /api/intake/psychological creates person
    post_data = {
        "display_name": "Kavya Menon",
        "one_liner": "Pediatric Surgeon & Wilderness Trail Runner",
        "archetype_preference": "grounded_sanctuary",
        "sunday_rhythm": "5 AM mountain trail run, farmer's market vegetables, baking sourdough with family.",
        "geo_anchor": "Permanently rooted locally; cannot relocate.",
        "family_vision": "Excited for children and large family dinners.",
        "social_battery": "Warm balanced battery; loves intimate domestic dinners.",
        "work_ambition": "Intense hospital shifts, but leaves work completely at hospital doors.",
        "financial_philosophy": "Conscious living and investing in long-term family stability.",
        "future_vision": "Dream is to build a rural pediatric wellness center alongside a family farm.",
        "attachment_choice": "secure",
        "conflict_choice": "collaborative",
        "dealbreakers": "Digital nomads wanting to relocate every 6 months, heavy smoking, cynicism.",
        "ideal_date": "An outdoor botanical garden tea pavilion.",
    }

    res_post = client.post("/api/intake/psychological", data=post_data, follow_redirects=False)
    assert res_post.status_code == 303
    redirect_url = res_post.headers["location"]
    assert redirect_url.startswith("/person/user-")

    pid = redirect_url.split("/person/")[1]
    saved_person = store.get_person(pid)
    assert saved_person is not None
    assert saved_person.analysis.archetype == "The Grounded Sanctuary"
    assert saved_person.analysis.attachment_style == "Secure"
    assert saved_person.analysis.future_horizon == post_data["future_vision"]


def test_dating_agents_embody_psychological_persona():
    """Verify autonomous dating agents incorporate psychological archetypes and attachment dynamics."""
    answers_a = {
        "archetype_preference": "contemplative_craftsman",
        "sunday_rhythm": "Comfortable silence and parallel bookbinding in morning light.",
        "geo_anchor": "Rooted locally",
        "future_vision": "Steward a quiet craft retreat in the mountains",
        "attachment_choice": "secure",
        "conflict_choice": "collaborative",
        "dealbreakers": "Loud aggressive partying every night",
        "ideal_date": "Quiet tea house with ambient music",
    }
    p_a = synthesize_psychological_persona("Arun", "Bookbinder", answers_a, pid="test-p-a")

    answers_b = {
        "archetype_preference": "empathic_healer",
        "sunday_rhythm": "Quiet pour-over coffee, watercolor painting, gentle trail walks.",
        "geo_anchor": "Rooted locally",
        "future_vision": "Steward a quiet craft retreat in the mountains",
        "attachment_choice": "secure",
        "conflict_choice": "collaborative",
        "dealbreakers": "Mocking feelings, cynicism",
        "ideal_date": "Quiet tea house with ambient music",
    }
    p_b = synthesize_psychological_persona("Tara", "Art Therapist", answers_b, pid="test-p-b")

    date_record = dater.go_on_date(
        p_a.id,
        p_a.analysis,
        p_b.id,
        p_b.analysis,
        coaching_a=p_a.coaching_notes,
        coaching_b=p_b.coaching_notes,
    )

    assert date_record.mutual > 8.0
    assert date_record.verdict_a.second_date is True
    assert date_record.verdict_b.second_date is True
    
    # Learned mental model captures psychological archetype
    learned_a = date_record.verdict_a.learned_about_other
    assert any("The Empathic Healer" in item for item in learned_a)
