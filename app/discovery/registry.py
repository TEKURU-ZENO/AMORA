from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..store import _conn
from .models import DiscoveryCandidate


def init() -> None:
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS candidate_registry (
                id TEXT PRIMARY KEY,
                linkedin_url TEXT NOT NULL,
                instagram_url TEXT,
                status TEXT NOT NULL,
                verification_method TEXT,
                verification_evidence TEXT,
                rejection_reason TEXT,
                invitation_token TEXT UNIQUE,
                body TEXT NOT NULL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_candidate_token ON candidate_registry(invitation_token)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_candidate_status ON candidate_registry(status)")


def save_candidate(cand: DiscoveryCandidate) -> None:
    init()
    cand.updated_at = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        c.execute("""
            INSERT OR REPLACE INTO candidate_registry
            (id, linkedin_url, instagram_url, status, verification_method, verification_evidence, rejection_reason, invitation_token, body)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cand.id,
            cand.linkedin_url,
            cand.instagram_url,
            cand.status,
            cand.verification_method,
            cand.verification_evidence,
            cand.rejection_reason,
            cand.invitation_token,
            cand.model_dump_json()
        ))


def get_candidate(cid: str) -> DiscoveryCandidate | None:
    init()
    with _conn() as c:
        row = c.execute("SELECT body FROM candidate_registry WHERE id = ?", (cid,)).fetchone()
    return DiscoveryCandidate.model_validate_json(row[0]) if row else None


def get_candidate_by_token(token: str) -> DiscoveryCandidate | None:
    init()
    if not token:
        return None
    with _conn() as c:
        row = c.execute("SELECT body FROM candidate_registry WHERE invitation_token = ?", (token,)).fetchone()
    return DiscoveryCandidate.model_validate_json(row[0]) if row else None


def list_candidates(status: Optional[str] = None) -> list[DiscoveryCandidate]:
    init()
    with _conn() as c:
        if status:
            rows = c.execute("SELECT body FROM candidate_registry WHERE status = ? ORDER BY rowid DESC", (status,)).fetchall()
        else:
            rows = c.execute("SELECT body FROM candidate_registry ORDER BY rowid DESC").fetchall()
    return [DiscoveryCandidate.model_validate_json(r[0]) for r in rows]


def delete_candidate(cid: str) -> None:
    init()
    with _conn() as c:
        c.execute("DELETE FROM candidate_registry WHERE id = ?", (cid,))


def update_status(cid: str, status: str, evidence: str = "", reason: str = "") -> DiscoveryCandidate | None:
    cand = get_candidate(cid)
    if not cand:
        return None
    cand.status = status
    if evidence:
        cand.verification_evidence = evidence
    if reason:
        cand.rejection_reason = reason
    save_candidate(cand)
    return cand
