"""Authentication and multi-tenant session management for AMORA SaaS.

Supports:
- Passwordless email sign-in / demo 1-click accounts.
- Persistent session cookies and Bearer tokens.
- Secure persona claiming and tenancy isolation.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Optional
from fastapi import HTTPException, Request, Response

from .. import store
from .models import PlanTier, User


def init_auth_tables() -> None:
    """Ensure multi-tenant SaaS tables exist in the SQLite store."""
    with store._conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                body TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_uid ON sessions(user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")


def save_user(user: User) -> None:
    init_auth_tables()
    with store._conn() as c:
        c.execute("INSERT OR REPLACE INTO users (id, email, body) VALUES (?, ?, ?)",
                  (user.id, user.email.lower().strip(), user.model_dump_json()))


def get_user(uid: str) -> Optional[User]:
    init_auth_tables()
    with store._conn() as c:
        row = c.execute("SELECT body FROM users WHERE id=?", (uid,)).fetchone()
    return User.model_validate_json(row[0]) if row else None


def get_user_by_email(email: str) -> Optional[User]:
    init_auth_tables()
    clean_email = email.lower().strip()
    with store._conn() as c:
        row = c.execute("SELECT body FROM users WHERE email=?", (clean_email,)).fetchone()
    return User.model_validate_json(row[0]) if row else None


def create_or_get_user(email: str, name: str = "", plan: PlanTier = "free", person_id: Optional[str] = None) -> User:
    """Find existing user or create a new user account."""
    clean_email = email.lower().strip()
    existing = get_user_by_email(clean_email)
    if existing:
        updated = False
        if person_id and not existing.person_id:
            existing.person_id = person_id
            updated = True
        if name and not existing.name:
            existing.name = name
            updated = True
        if updated:
            save_user(existing)
        return existing

    uid = "usr_" + secrets.token_hex(8)
    user = User(
        id=uid,
        email=clean_email,
        name=name,
        person_id=person_id,
        plan=plan,
    )
    save_user(user)
    return user


def create_session(user_id: str) -> str:
    """Generate a high-entropy session token and record in SQLite."""
    init_auth_tables()
    token = "sess_" + secrets.token_urlsafe(32)
    with store._conn() as c:
        c.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
    return token


def get_user_by_session(token: str) -> Optional[User]:
    if not token:
        return None
    init_auth_tables()
    with store._conn() as c:
        row = c.execute("""
            SELECT u.body FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ?
        """, (token,)).fetchone()
    return User.model_validate_json(row[0]) if row else None


def delete_session(token: str) -> None:
    if not token:
        return
    init_auth_tables()
    with store._conn() as c:
        c.execute("DELETE FROM sessions WHERE token=?", (token,))


def link_person_to_user(user_id: str, person_id: str) -> User:
    """Associate a candidate persona to an authenticated user account."""
    user = get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    user.person_id = person_id
    save_user(user)
    return user


def get_current_user(request: Request) -> Optional[User]:
    """Retrieve authenticated user from cookie or Authorization header."""
    # 1. Cookie
    token = request.cookies.get("amora_session")
    if token:
        u = get_user_by_session(token)
        if u:
            return u

    # 2. Authorization header: Bearer <session_token>
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        bearer_token = auth[7:].strip()
        u = get_user_by_session(bearer_token)
        if u:
            return u

    # 3. Custom header
    custom_hdr = request.headers.get("X-Amora-Session")
    if custom_hdr:
        u = get_user_by_session(custom_hdr)
        if u:
            return u

    return None


def require_current_user(request: Request) -> User:
    """Enforce authentication; raises 401 if unauthenticated."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(401, detail="Authentication required. Please log in.")
    return user


def set_session_cookie(response: Response, token: str) -> None:
    """Set secure HTTP-only session cookie."""
    response.set_cookie(
        key="amora_session",
        value=token,
        httponly=True,
        max_age=30 * 24 * 3600,  # 30 days
        samesite="lax",
        secure=False,  # localhost friendly; in strict TLS production reverse proxy handles it
    )


def clear_session_cookie(response: Response) -> None:
    """Clear session cookie on logout."""
    response.delete_cookie(key="amora_session")
