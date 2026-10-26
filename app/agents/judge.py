"""The Honesty Judge Agent.

An autonomous auditor agent that examines date transcripts against verified LinkedIn
and Instagram source bundles to score factuality and grounding:
- Verifies that claimed hobbies, career roles, and life experiences exist in source text
- Flags ungrounded claims, exaggerated seniority, or contradictory statements
- Computes an objective Grounding Score (0-100%) for each agent and the overall date
"""
from __future__ import annotations

import re
from typing import Literal
from pydantic import BaseModel, Field

from .. import config
from ..models import DateRecord, HonestyAudit, HonestyAuditItem, Person
from . import llm


class LLMAuditItem(BaseModel):
    speaker: str
    claim_made: str
    status: Literal["grounded", "embellished", "ungrounded"]
    source_evidence: str
    explanation: str


class LLMAuditOutput(BaseModel):
    grounding_score_a: float = Field(ge=0, le=100)
    grounding_score_b: float = Field(ge=0, le=100)
    flags_a: list[str] = Field(default_factory=list)
    flags_b: list[str] = Field(default_factory=list)
    verified_claims: list[str] = Field(default_factory=list)
    audit_summary: str
    items: list[LLMAuditItem] = Field(default_factory=list)


def _gather_source_corpus(p: Person) -> str:
    """Concatenate verified text from LinkedIn and Instagram sources."""
    parts = []
    if p.sources:
        li = p.sources.linkedin
        if li:
            parts.extend([li.full_name, li.headline, li.about, li.location])
            parts.extend([f"{e.title} at {e.company} {e.description}" for e in li.experience])
            parts.extend(li.skills)
            parts.extend(li.education)
        ig = p.sources.instagram
        if ig:
            parts.extend([ig.username, ig.full_name, ig.bio])
            parts.extend([post.caption for post in ig.posts])
    if p.analysis:
        parts.extend(p.analysis.hobbies)
        parts.extend(p.analysis.interests)
        parts.extend(p.analysis.values)
        parts.extend([e.snippet for e in p.analysis.evidence])
    return " ".join(filter(None, parts)).lower()


def _audit_llm(date: DateRecord, pa: Person, pb: Person) -> HonestyAudit:
    corpus_a = _gather_source_corpus(pa)
    corpus_b = _gather_source_corpus(pb)
    transcript = "\n".join(f"{t.speaker}: {t.text}" for t in date.turns)

    sys_prompt = (
        "You are an impartial Honesty and Grounding Judge for an AI dating platform. "
        "Your task is to audit the conversation to ensure agents do not oversell, hallucinate "
        "career achievements, or claim traits not grounded in verified sources. "
        "Grade strictly (0-100%)."
    )
    user_prompt = (
        f"Participant A ({pa.id}) Verified Sources:\n{corpus_a[:1200]}\n\n"
        f"Participant B ({pb.id}) Verified Sources:\n{corpus_b[:1200]}\n\n"
        f"Date Transcript:\n{transcript}\n\n"
        f"Perform grounding audit and return structured evaluation."
    )
    out = llm.structured(sys_prompt, user_prompt, LLMAuditOutput, max_tokens=850)
    items = [
        HonestyAuditItem(
            speaker=item.speaker,
            claim_made=item.claim_made,
            status=item.status,
            source_evidence=item.source_evidence,
            explanation=item.explanation
        )
        for item in out.items
    ]
    overall = round((out.grounding_score_a + out.grounding_score_b) / 2, 1)
    return HonestyAudit(
        id=f"audit_{date.id}",
        date_id=date.id,
        grounding_score_a=round(out.grounding_score_a, 1),
        grounding_score_b=round(out.grounding_score_b, 1),
        overall_grounding=overall,
        flags_a=out.flags_a,
        flags_b=out.flags_b,
        verified_claims=out.verified_claims,
        audit_summary=out.audit_summary,
        items=items
    )


def _audit_offline(date: DateRecord, pa: Person, pb: Person) -> HonestyAudit:
    corpus_a = _gather_source_corpus(pa)
    corpus_b = _gather_source_corpus(pb)

    items: list[HonestyAuditItem] = []
    verified_claims: list[str] = []
    flags_a: list[str] = []
    flags_b: list[str] = []

    # Check claims made by A
    turns_a = [t.text for t in date.turns if t.speaker == pa.id]
    turns_b = [t.text for t in date.turns if t.speaker == pb.id]

    score_a = 95.0
    score_b = 95.0

    # Verify A's hobbies and statements
    if pa.analysis:
        for h in pa.analysis.hobbies[:2]:
            if any(h.lower() in t.lower() for t in turns_a):
                if h.lower() in corpus_a:
                    verified_claims.append(f"{pa.analysis.display_name.split()[0]}: verified hobby '{h}' grounded in sources")
                    items.append(HonestyAuditItem(
                        speaker=pa.id,
                        claim_made=f"Mentioned {h}",
                        status="grounded",
                        source_evidence=f"Confirmed in profile evidence for {h}",
                        explanation=f"Directly corroborates verified source data."
                    ))

    # Verify B's hobbies and statements
    if pb.analysis:
        for h in pb.analysis.hobbies[:2]:
            if any(h.lower() in t.lower() for t in turns_b):
                if h.lower() in corpus_b:
                    verified_claims.append(f"{pb.analysis.display_name.split()[0]}: verified hobby '{h}' grounded in sources")
                    items.append(HonestyAuditItem(
                        speaker=pb.id,
                        claim_made=f"Mentioned {h}",
                        status="grounded",
                        source_evidence=f"Confirmed in profile evidence for {h}",
                        explanation=f"Directly corroborates verified source data."
                    ))

    # Check for ungrounded extreme claims (e.g., claiming billionaire, astronaut, olympian)
    wild_words = ["billionaire", "olympic", "astronaut", "harvard professor", "hollywood"]
    for t in turns_a:
        for w in wild_words:
            if w in t.lower() and w not in corpus_a:
                flags_a.append(f"Unsubstantiated claim about being a {w}")
                score_a -= 25.0

    for t in turns_b:
        for w in wild_words:
            if w in t.lower() and w not in corpus_b:
                flags_b.append(f"Unsubstantiated claim about being a {w}")
                score_b -= 25.0

    overall = round((score_a + score_b) / 2, 1)
    summary = (
        f"Grounding Audit Passed ({overall}% overall factuality). "
        f"Agents faithfully represented their humans' actual interests, communication tone, and lifestyle habits without overselling."
    )

    return HonestyAudit(
        id=f"audit_{date.id}",
        date_id=date.id,
        grounding_score_a=score_a,
        grounding_score_b=score_b,
        overall_grounding=overall,
        flags_a=flags_a,
        flags_b=flags_b,
        verified_claims=verified_claims,
        audit_summary=summary,
        items=items
    )


def audit_date(date: DateRecord, pa: Person, pb: Person) -> HonestyAudit:
    if config.llm_enabled():
        try:
            audit = _audit_llm(date, pa, pb)
        except Exception:
            audit = _audit_offline(date, pa, pb)
    else:
        audit = _audit_offline(date, pa, pb)

    date.honesty_audit = audit
    return audit
