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
from .models import DateRecord, FirstFightRecord, GroupDateRecord, GroupTurn, HonestyAudit, Person, SecondDatePlan, StressTurn, StressVerdict, Turn, Verdict


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
    return Turn(speaker=t.speaker, text=t.text, thought="", observation="", mood=t.mood, whisper=None)


def sanitize_verdict(v: Verdict, authorized: bool = False) -> Verdict:
    """Mask private agent reports and date revelations unless authorized."""
    if authorized:
        return v
    v_copy = v.model_copy()
    v_copy.report_to_human = "[Private agent report to human]"
    v_copy.learned_about_other = ["[Private agent discovery]"]
    return v_copy


def sanitize_stress_turn(t: StressTurn, authorized: bool = False) -> StressTurn:
    """Mask private stress thoughts unless authorized."""
    if authorized:
        return t
    return StressTurn(speaker=t.speaker, text=t.text, thought="", emotional_tone=t.emotional_tone)


def sanitize_first_fight(ff: Optional[FirstFightRecord], authorized: bool = False) -> Optional[FirstFightRecord]:
    """Mask private conflict analysis in first fight scenario unless authorized."""
    if not ff:
        return None
    if authorized:
        return ff
    sanitized_turns = [sanitize_stress_turn(t, authorized=False) for t in ff.turns]
    va = ff.verdict_a.model_copy()
    vb = ff.verdict_b.model_copy()
    va.key_takeaway = "[Private conflict analysis]"
    vb.key_takeaway = "[Private conflict analysis]"
    return ff.model_copy(update={
        "turns": sanitized_turns,
        "verdict_a": va,
        "verdict_b": vb,
    })


def sanitize_second_date_plan(plan: Optional[SecondDatePlan], authorized: bool = False) -> Optional[SecondDatePlan]:
    """Mask private drafted intro messages unless authorized."""
    if not plan:
        return None
    if authorized:
        return plan
    p_copy = plan.model_copy()
    p_copy.drafted_intro_for_a = "[Private drafted message for human]"
    p_copy.drafted_intro_for_b = "[Private drafted message for human]"
    return p_copy


def sanitize_group_turn(t: GroupTurn, authorized: bool = False) -> GroupTurn:
    if authorized:
        return t
    return GroupTurn(speaker=t.speaker, text=t.text, thought="", target=t.target)


def sanitize_group_date(gd: GroupDateRecord, authorized: bool = False) -> GroupDateRecord:
    if authorized:
        return gd
    return gd.model_copy(update={
        "turns": [sanitize_group_turn(t, authorized=False) for t in gd.turns]
    })


def sanitize_date(d: DateRecord, authorized: bool = False) -> DateRecord:
    """Return a DateRecord copy with private thoughts, observations and internal reports masked if unauthorized."""
    if authorized:
        return d
    sanitized_turns = [sanitize_turn(t, authorized=False) for t in d.turns]
    va = sanitize_verdict(d.verdict_a, authorized=False)
    vb = sanitize_verdict(d.verdict_b, authorized=False)
    s_ff = sanitize_first_fight(d.first_fight, authorized=authorized)
    s_plan = sanitize_second_date_plan(d.second_date_plan, authorized=authorized)
    return d.model_copy(update={
        "turns": sanitized_turns,
        "verdict_a": va,
        "verdict_b": vb,
        "observations_a": [],
        "observations_b": [],
        "first_fight": s_ff,
        "second_date_plan": s_plan,
    })


def sanitize_date_dict(d: DateRecord, authorized: bool = False) -> dict:
    """Return serialized dict of date, stripping private thoughts when unauthorized."""
    return sanitize_date(d, authorized).model_dump()


def sanitize_person_dict(p: Person, authorized: bool = False) -> dict:
    """Serialize person, hiding raw scraped source data and private coaching instructions from unauthorized public view."""
    return p.model_dump(exclude={"sources", "coaching_notes", "feedback_history"} if not authorized else None)


def verify_person_access(request: Request, p: Person, token: Optional[str] = None) -> bool:
    """Verify if the caller has authority to edit, coach, feedback, or delete this person.

    Authorized if:
    1. Caller provides administrative / demo credentials (is_authorized(request)).
    2. Per-person secret edit token matches p.edit_token (from parameter, query ?token=, header X-Person-Token, or cookie).
    3. Authenticated SaaS user owns this persona (current_user.person_id == p.id).
    """
    if not p:
        return False

    # 1. Admin / demo authorization
    if is_authorized(request):
        return True

    # 2. Check per-person secret edit token
    cand_token = (
        token
        or request.query_params.get("token")
        or request.headers.get("X-Person-Token")
        or request.cookies.get(f"amora_token_{p.id}")
    )
    if cand_token and getattr(p, "edit_token", None):
        if hmac.compare_digest(cand_token.strip(), p.edit_token.strip()):
            return True

    # 3. Check SaaS authenticated user ownership
    try:
        from . import saas
        user = saas.get_current_user(request)
        if user and user.person_id == p.id:
            return True
    except Exception:
        pass

    return False


def require_person_access(request: Request, p: Person, token: Optional[str] = None) -> None:
    """Raise 403 Forbidden if the caller lacks authorization to modify or delete this person."""
    if not verify_person_access(request, p, token=token):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: You do not have permission to modify or delete this profile. A valid per-person token, owner session, or admin key is required."
        )
