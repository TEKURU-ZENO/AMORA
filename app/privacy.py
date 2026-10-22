"""Privacy boundary and access control layer for AMORA.

Enforces:
1. Stripping private inner agent monologue (Turn.thought) from unauthorized views and public exports.
2. Masking private agent briefs and verdicts in unauthorized replays.
3. Access checks for administrative and bulk-export endpoints.
4. Consent revocation and cascading data cleanup.
"""
from __future__ import annotations

import hmac
import os
from typing import Optional
from fastapi import HTTPException, Request


from . import config
from .models import DateRecord, Person, Turn, Verdict


def is_authorized(request: Request) -> bool:
    """Check if the incoming request has valid administrative or demo credentials."""
    expected = os.getenv("ADMIN_API_KEY") or config.ADMIN_API_KEY
    if not expected:
        return False


    # Check X-Amora-Key header (X-AgentDate-Key still accepted)
    header_key = request.headers.get("X-Amora-Key") or request.headers.get("X-AgentDate-Key")
    if header_key and hmac.compare_digest(header_key, expected):
        return True

    # Check Authorization: Bearer <key>
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if hmac.compare_digest(token, expected):
            return True

    # Check query parameter demo_key / key / admin_key
    qp = request.query_params
    query_key = qp.get("demo_key") or qp.get("key") or qp.get("admin_key")
    if query_key and hmac.compare_digest(query_key, expected):
        return True

    # Check cookie
    cookie_key = request.cookies.get("amora_key") or request.cookies.get("agentdate_key")
    if cookie_key and hmac.compare_digest(cookie_key, expected):
        return True

    return False


def require_auth(request: Request) -> None:
    """Raise 401 if request is unauthorized."""
    if not is_authorized(request):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Valid X-Amora-Key or demo_key required for this resource."
        )


def sanitize_turn(t: Turn, authorized: bool = False) -> Turn:
    """Mask private agent thoughts and running observations unless authorized."""
    if authorized:
        return t
    return Turn(speaker=t.speaker, text=t.text, thought="", observation="")


def sanitize_verdict(v: Verdict, authorized: bool = False) -> Verdict:
    """Mask private agent reports and date revelations unless authorized."""
    if authorized:
        return v
    v_copy = v.model_copy()
    v_copy.report_to_human = "[Private agent report to human]"
    v_copy.learned_about_other = ["[Private agent discovery]"]
    return v_copy


def sanitize_date(d: DateRecord, authorized: bool = False) -> DateRecord:
    """Return a DateRecord copy with private thoughts, observations and internal reports masked if unauthorized."""
    if authorized:
        return d
    sanitized_turns = [sanitize_turn(t, authorized=False) for t in d.turns]
    va = sanitize_verdict(d.verdict_a, authorized=False)
    vb = sanitize_verdict(d.verdict_b, authorized=False)
    return d.model_copy(update={
        "turns": sanitized_turns,
        "verdict_a": va,
        "verdict_b": vb,
        "observations_a": [],
        "observations_b": [],
    })


def sanitize_date_dict(d: DateRecord, authorized: bool = False) -> dict:
    """Return serialized dict of date, stripping private thoughts when unauthorized."""
    return sanitize_date(d, authorized).model_dump()


def sanitize_person_dict(p: Person, authorized: bool = False) -> dict:
    """Serialize person, hiding raw scraped source data and private coaching instructions from unauthorized public view."""
    return p.model_dump(exclude={"sources", "coaching_notes", "feedback_history"} if not authorized else None)
