"""Notification Center for AMORA SaaS.

Manages in-app notifications, algorithmic match alerts, date summaries,
and dealbreaker protection notices for authenticated users.
"""
from __future__ import annotations

import secrets
import time
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

from . import store
from .models import DateRecord


NotificationType = Literal[
    "stable_match",
    "date_completed",
    "dealbreaker_alert",
    "whisper_ack",
    "system",
]


class Notification(BaseModel):
    id: str
    user_id: str
    type: NotificationType
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool = False
    created_at: str = Field(
        default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    )


def init_notification_tables() -> None:
    """Ensure notifications table and indexes exist in SQLite store."""
    with store._conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                link TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                body TEXT NOT NULL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_notifications_uid ON notifications(user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_notifications_uid_read ON notifications(user_id, is_read)")


def create_notification(
    user_id: str,
    title: str,
    message: str,
    type: NotificationType = "system",
    link: Optional[str] = None,
) -> Notification:
    """Create and persist a new notification for a user."""
    init_notification_tables()
    nid = "notif_" + secrets.token_hex(8)
    notif = Notification(
        id=nid,
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        link=link,
        is_read=False,
    )
    with store._conn() as c:
        c.execute(
            """
            INSERT INTO notifications (id, user_id, type, title, message, link, is_read, created_at, body)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                notif.id,
                notif.user_id,
                notif.type,
                notif.title,
                notif.message,
                notif.link,
                0,
                notif.created_at,
                notif.model_dump_json(),
            ),
        )
    return notif


def list_notifications(user_id: str, limit: int = 50) -> list[Notification]:
    """Retrieve recent notifications for a user, newest first."""
    init_notification_tables()
    with store._conn() as c:
        rows = c.execute(
            """
            SELECT body FROM notifications
            WHERE user_id = ?
            ORDER BY rowid DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [Notification.model_validate_json(r[0]) for r in rows]


def count_unread_notifications(user_id: str) -> int:
    """Count unread notifications for navbar badges."""
    init_notification_tables()
    with store._conn() as c:
        row = c.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
            (user_id,),
        ).fetchone()
    return row[0] if row else 0


def mark_as_read(notification_id: str, user_id: str) -> bool:
    """Mark a single notification as read if owned by the user."""
    init_notification_tables()
    with store._conn() as c:
        cursor = c.execute(
            "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
            (notification_id, user_id),
        )
        if cursor.rowcount > 0:
            row = c.execute("SELECT body FROM notifications WHERE id = ?", (notification_id,)).fetchone()
            if row:
                notif = Notification.model_validate_json(row[0])
                notif.is_read = True
                c.execute(
                    "UPDATE notifications SET body = ? WHERE id = ?",
                    (notif.model_dump_json(), notification_id),
                )
            return True
    return False


def mark_all_as_read(user_id: str) -> int:
    """Mark all notifications for a user as read."""
    init_notification_tables()
    with store._conn() as c:
        rows = c.execute(
            "SELECT id, body FROM notifications WHERE user_id = ? AND is_read = 0",
            (user_id,),
        ).fetchall()
        for nid, body in rows:
            notif = Notification.model_validate_json(body)
            notif.is_read = True
            c.execute(
                "UPDATE notifications SET is_read = 1, body = ? WHERE id = ?",
                (notif.model_dump_json(), nid),
            )
        return len(rows)


def dispatch_round_notifications(dates: list[DateRecord]) -> int:
    """Scan newly completed dates and dispatch targeted alerts to persona owners.

    Returns the count of dispatched notifications.
    """
    from . import saas

    init_notification_tables()
    # Map all users by their claimed person_id
    users_by_pid: dict[str, Any] = {}
    with store._conn() as c:
        rows = c.execute("SELECT id, body FROM users").fetchall()
        for _, ubody in rows:
            try:
                u = saas.models.User.model_validate_json(ubody)
                if u.person_id:
                    users_by_pid[u.person_id] = u
            except Exception:
                pass

    if not users_by_pid:
        return 0

    people_by_id = {p.id: p for p in store.list_persons()}
    dispatched = 0

    for d in dates:
        # Check person A
        if d.a in users_by_pid:
            user_a = users_by_pid[d.a]
            partner_b = people_by_id.get(d.b)
            name_b = (
                partner_b.analysis.display_name
                if partner_b and partner_b.analysis
                else "Partner"
            )

            # Dealbreaker alert
            if d.verdict_a.dealbreaker_hit:
                create_notification(
                    user_id=user_a.id,
                    title=f"Dealbreaker Protected: {name_b}",
                    message=f"Your agent respectfully declined a second date with {name_b} after detecting an incompatible dealbreaker during conversation.",
                    type="dealbreaker_alert",
                    link=f"/date/{d.id}",
                )
                dispatched += 1
            # High compatibility alert
            elif d.mutual >= 7.0 and d.verdict_a.second_date and d.verdict_b.second_date:
                create_notification(
                    user_id=user_a.id,
                    title=f"Mutual Spark! {name_b} ({d.mutual:.1f}/10)",
                    message=f"Both agents enthusiastically agreed to a second date at {d.venue}! Match Dossier and AI icebreakers are now available.",
                    type="date_completed",
                    link=f"/date/{d.id}/match-packet",
                )
                dispatched += 1
            else:
                create_notification(
                    user_id=user_a.id,
                    title=f"Date Replay Ready: {name_b}",
                    message=f"Your agent finished chatting with {name_b} at {d.venue} with a mutual compatibility score of {d.mutual:.1f}/10.",
                    type="date_completed",
                    link=f"/date/{d.id}",
                )
                dispatched += 1

        # Check person B
        if d.b in users_by_pid:
            user_b = users_by_pid[d.b]
            partner_a = people_by_id.get(d.a)
            name_a = (
                partner_a.analysis.display_name
                if partner_a and partner_a.analysis
                else "Partner"
            )

            if d.verdict_b.dealbreaker_hit:
                create_notification(
                    user_id=user_b.id,
                    title=f"Dealbreaker Protected: {name_a}",
                    message=f"Your agent protected your boundaries and declined a second date with {name_a}.",
                    type="dealbreaker_alert",
                    link=f"/date/{d.id}",
                )
                dispatched += 1
            elif d.mutual >= 7.0 and d.verdict_a.second_date and d.verdict_b.second_date:
                create_notification(
                    user_id=user_b.id,
                    title=f"Mutual Spark! {name_a} ({d.mutual:.1f}/10)",
                    message=f"Both agents agreed to a second date at {d.venue}! Match Dossier is ready.",
                    type="date_completed",
                    link=f"/date/{d.id}/match-packet",
                )
                dispatched += 1
            else:
                create_notification(
                    user_id=user_b.id,
                    title=f"Date Replay Ready: {name_a}",
                    message=f"Your agent finished chatting with {name_a} at {d.venue} (Score: {d.mutual:.1f}/10).",
                    type="date_completed",
                    link=f"/date/{d.id}",
                )
                dispatched += 1

    # Check for newly formed Irving stable matches
    meta_rankings = store.get_meta("rankings", {}) or {}
    stable_pairs = meta_rankings.get("stable_pairs", [])
    for pair in stable_pairs:
        p1_id, p2_id = pair.get("a"), pair.get("b")
        p1 = people_by_id.get(p1_id)
        p2 = people_by_id.get(p2_id)
        name1 = p1.analysis.display_name if p1 and p1.analysis else p1_id
        name2 = p2.analysis.display_name if p2 and p2.analysis else p2_id

        if p1_id in users_by_pid:
            u1 = users_by_pid[p1_id]
            create_notification(
                user_id=u1.id,
                title=f"★ Irving Stable Match Confirmed: {name2}",
                message=f"AMORA's Irving Stable Roommates algorithm matched you and {name2} with 0 blocking pairs across the entire pool!",
                type="stable_match",
                link="/my-agent",
            )
            dispatched += 1

        if p2_id in users_by_pid:
            u2 = users_by_pid[p2_id]
            create_notification(
                user_id=u2.id,
                title=f"★ Irving Stable Match Confirmed: {name1}",
                message=f"AMORA's Irving Stable Roommates algorithm matched you and {name1} with 0 blocking pairs across the entire pool!",
                type="stable_match",
                link="/my-agent",
            )
            dispatched += 1

    return dispatched
