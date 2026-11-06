"""Tests for Zero-Scraping Onboarding: AI Intake Interview & LinkedIn PDF Ingestion."""
import io
import pytest
from reportlab.pdfgen import canvas
from starlette.testclient import TestClient

from app import harness, store
from app.intake import parse_linkedin_pdf, synthesize_interview_persona
from app.main import app
from app.saas import create_or_get_user, create_session
from tests.conftest import seed_pool


@pytest.fixture(scope="module", autouse=True)
def setup_test_suite():
    store.init()
    store.clear_all()
    seed_pool(6)
    harness.run_round(progress=lambda m: None)


def _generate_test_linkedin_pdf(name: str, headline: str) -> bytes:
    """Generate a realistic in-memory LinkedIn export PDF."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(50, 750, name)
    c.drawString(50, 735, headline)
    c.drawString(50, 720, "San Francisco Bay Area")
    c.drawString(50, 690, "Summary")
    c.drawString(50, 675, "Passionate about building resilient distributed systems and quiet mountain trail walks.")
    c.drawString(50, 645, "Experience")
    c.drawString(50, 630, "Principal Software Architect")
    c.drawString(50, 615, "Scale Distributed Labs")
    c.drawString(50, 585, "Skills")
    c.drawString(50, 570, "Python, Distributed Systems, Architecture")
    c.save()
    return buf.getvalue()


def test_ai_intake_interview_synthesis():
    """Verify conversational interview answers synthesize a grounded Person model."""
    answers = {
        "sunday_rhythm": "Quiet pour-over coffee, reading philosophy in morning sunlight, trail hike, then parallel studio creative work.",
        "dealbreakers": "Moving abroad (anchored in city for family), emotional avoidance or stonewalling, workaholism without boundaries.",
        "communication": "I need 20 minutes to decompress quietly, then direct and emotionally honest check-ins.",
        "latent_passions": "Building an off-grid wildlife sanctuary cabin in the Pacific Northwest.",
        "ideal_date": "A quiet corner booth at a neighborhood tea lounge where we can actually talk.",
    }

    person = synthesize_interview_persona(
        display_name="Tara Bose",
        one_liner="Environmental Scientist & Nature Illustrator",
        answers=answers,
    )

    assert person.id.startswith("intake-")
    assert person.analysis.display_name == "Tara Bose"
    assert person.analysis.lifestyle["pace"] == "Slow intentional living"
    assert len(person.analysis.dealbreakers) >= 2
    assert "Moving abroad (anchored in city for family)" in person.analysis.dealbreakers[0]
    assert len(person.analysis.evidence) >= 2
    assert "pour-over" in person.analysis.evidence[0].snippet.lower()
    assert len(person.coaching_notes) >= 1


def test_linkedin_pdf_parsing():
    """Verify parsing LinkedIn PDF bytes extracts experience, skills, and synthesizes Analysis."""
    pdf_bytes = _generate_test_linkedin_pdf("Dev Mehta", "Senior Systems Architect & Open-Source Builder")
    person = parse_linkedin_pdf(pdf_bytes)

    assert person.id.startswith("pdf-")
    assert person.analysis.display_name == "Dev Mehta"
    assert "Senior Systems Architect" in person.analysis.one_liner
    assert len(person.sources.linkedin.experience) >= 1
    assert person.sources.linkedin.experience[0].title == "Principal Software Architect"
    assert "Python" in person.sources.linkedin.skills[0]
    assert len(person.analysis.evidence) >= 1
    assert person.analysis.confidence >= 0.9


def test_intake_http_endpoints():
    """Verify GET /intake and POST /api/intake/interview and POST /api/intake/pdf."""
    client = TestClient(app)

    # 1. GET /intake page
    res_page = client.get("/intake")
    assert res_page.status_code == 200
    assert "Build Your Autonomous Dating Agent" in res_page.text
    assert "3-Minute Agent Interview" in res_page.text
    assert "Upload LinkedIn PDF" in res_page.text

    # 2. POST /api/intake/interview (Authenticated SaaS user)
    user = create_or_get_user("interview_user@amora.date", name="Interview Tester", plan="pro")
    sess_token = create_session(user.id)
    client.cookies.set("amora_session", sess_token)

    res_interview = client.post(
        "/api/intake/interview",
        data={
            "display_name": "Arjun Patel",
            "one_liner": "Robotics Researcher & Classical Guitarist",
            "sunday_rhythm": "Quiet morning espresso, acoustic guitar practice, then an early mountain bike ride.",
            "dealbreakers": "Disrespecting boundaries, emotional defensiveness, smoking.",
            "communication": "Direct and respectful.",
            "latent_passions": "Restoring vintage musical instruments.",
            "ideal_date": "An intimate jazz café.",
        },
        follow_redirects=False,
    )
    assert res_interview.status_code == 303
    assert res_interview.headers["location"] == "/my-agent"

    # Verify user is linked and has dates
    from app.saas import get_user
    u = get_user(user.id)
    assert u.person_id is not None
    p = store.get_person(u.person_id)
    assert p.analysis.display_name == "Arjun Patel"
    assert len(store.list_dates(p.id)) >= 1

    # 3. POST /api/intake/pdf (Upload PDF)
    pdf_bytes = _generate_test_linkedin_pdf("Kavita Rao", "Bioinformatics Scientist")
    res_pdf = client.post(
        "/api/intake/pdf",
        files={"pdf_file": ("kavita_profile.pdf", pdf_bytes, "application/pdf")},
        follow_redirects=False,
    )
    assert res_pdf.status_code == 303
    assert res_pdf.headers["location"] == "/my-agent"

    # Verify new person was saved
    u_updated = get_user(user.id)
    p_pdf = store.get_person(u_updated.person_id)
    assert p_pdf.analysis.display_name == "Kavita Rao"
    assert len(store.list_dates(p_pdf.id)) >= 1
