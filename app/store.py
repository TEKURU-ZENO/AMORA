"""Tiny SQLite document store. One JSON blob per person / date / run."""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager

from .config import DB_PATH, DATA_DIR
from .models import DateRecord, Person

_lock = threading.RLock()



@contextmanager
def _conn():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _lock:
        c = sqlite3.connect(DB_PATH)
        try:
            yield c
            c.commit()
        finally:
            c.close()


def init() -> None:
    with _conn() as c:
        c.execute("CREATE TABLE IF NOT EXISTS persons (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS dates (id TEXT PRIMARY KEY, a TEXT, b TEXT, body TEXT NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
        c.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                status TEXT NOT NULL,
                idempotency_key TEXT UNIQUE,
                entity_id TEXT,
                stage TEXT NOT NULL,
                stage_data TEXT,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("CREATE TABLE IF NOT EXISTS job_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, payload TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_jobs_idemp ON jobs(idempotency_key)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_job_logs_jid ON job_logs(job_id)")
    recover_interrupted_jobs()
    from . import config
    if not config.demo_mode():
        purge_synthetic()


def purge_synthetic() -> int:
    """The pool is Apify-scraped people only. Drop fictional personas left by older seed scripts."""
    with _conn() as c:
        ids = [r[0] for r in c.execute("SELECT id FROM persons WHERE json_extract(body, '$.synthetic') = 1")]
        for pid in ids:
            c.execute("DELETE FROM persons WHERE id=?", (pid,))
            c.execute("DELETE FROM dates WHERE a=? OR b=?", (pid, pid))
        if ids:  # rankings and asks were computed with them in the pool
            c.execute("DELETE FROM meta WHERE k IN ('rankings', 'asks')")
    return len(ids)



# ---- persons ----
def save_person(p: Person) -> None:
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO persons VALUES (?, ?)", (p.id, p.model_dump_json()))


def get_person(pid: str) -> Person | None:
    with _conn() as c:
        row = c.execute("SELECT body FROM persons WHERE id=?", (pid,)).fetchone()
    return Person.model_validate_json(row[0]) if row else None


def list_persons() -> list[Person]:
    with _conn() as c:
        rows = c.execute("SELECT body FROM persons").fetchall()
    ps = [Person.model_validate_json(r[0]) for r in rows]
    return sorted(ps, key=lambda p: (p.analysis.display_name if p.analysis else p.id).lower())


def delete_person(pid: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM persons WHERE id=?", (pid,))
        c.execute("DELETE FROM dates WHERE a=? OR b=?", (pid, pid))
    _cleanup_meta_references(pid)


def revoke_consent(pid: str) -> Person | None:
    """Revoke consent for a participant, mark status, purge dates, and clean references."""
    p = get_person(pid)
    if not p:
        return None
    p.consent = False
    p.status = "error"
    p.error = "Consent revoked by user"
    save_person(p)
    with _conn() as c:
        c.execute("DELETE FROM dates WHERE a=? OR b=?", (pid, pid))
    _cleanup_meta_references(pid)
    return p


def _cleanup_meta_references(pid: str) -> None:
    """Remove a person from asks and rankings meta structures."""
    asks = get_meta("asks", {}) or {}
    changed_asks = False
    new_asks = {}
    for k, picks in asks.items():
        if k == pid:
            changed_asks = True
            continue
        filtered_picks = [p for p in picks if p[0] != pid]
        if len(filtered_picks) != len(picks):
            changed_asks = True
        new_asks[k] = filtered_picks
    if changed_asks:
        set_meta("asks", new_asks)

    rankings = get_meta("rankings", {}) or {}
    changed_rankings = False
    new_rankings = {}
    for k, rows in rankings.items():
        if k == pid:
            changed_rankings = True
            continue
        filtered_rows = [r for r in rows if r.get("id") != pid]
        if len(filtered_rows) != len(rows):
            changed_rankings = True
        new_rankings[k] = filtered_rows
    if changed_rankings:
        set_meta("rankings", new_rankings)



# ---- dates ----
def save_date(d: DateRecord) -> None:
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO dates VALUES (?, ?, ?, ?)", (d.id, d.a, d.b, d.model_dump_json()))


def get_date(did: str) -> DateRecord | None:
    with _conn() as c:
        row = c.execute("SELECT body FROM dates WHERE id=?", (did,)).fetchone()
    return DateRecord.model_validate_json(row[0]) if row else None


def list_dates(pid: str | None = None) -> list[DateRecord]:
    with _conn() as c:
        if pid:
            rows = c.execute("SELECT body FROM dates WHERE a=? OR b=?", (pid, pid)).fetchall()
        else:
            rows = c.execute("SELECT body FROM dates").fetchall()
    ds = [DateRecord.model_validate_json(r[0]) for r in rows]
    return sorted(ds, key=lambda d: -d.mutual)


def clear_dates() -> None:
    with _conn() as c:
        c.execute("DELETE FROM dates")


def clear_all() -> None:
    with _conn() as c:
        c.execute("DELETE FROM persons")
        c.execute("DELETE FROM dates")
        c.execute("DELETE FROM meta")
        c.execute("DELETE FROM jobs")
        c.execute("DELETE FROM job_logs")
        # the discovery registry lives in the same file but is created lazily by its own module
        if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='candidate_registry'").fetchone():
            c.execute("DELETE FROM candidate_registry")



def set_meta(k: str, v) -> None:
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (k, json.dumps(v)))


def get_meta(k: str, default=None):
    with _conn() as c:
        row = c.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
    return json.loads(row[0]) if row else default


# ---- durable jobs ----
def create_or_get_job(job_id: str, job_type: str, idempotency_key: str | None = None, entity_id: str | None = None, stage: str = "init") -> tuple[dict, bool]:
    """Returns (job_dict, is_new). If an active job exists with idempotency_key, returns (existing, False).

    Only queued/running jobs are reused. A finished job must not block the next run, or a second
    dating round (key "round:active") or a re-join after deletion would silently never start."""
    with _conn() as c:
        if idempotency_key:
            row = c.execute("SELECT id, job_type, status, idempotency_key, entity_id, stage, stage_data, error FROM jobs WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if row:
                job = {
                    "id": row[0], "job_type": row[1], "status": row[2],
                    "idempotency_key": row[3], "entity_id": row[4],
                    "stage": row[5], "stage_data": json.loads(row[6]) if row[6] else {},
                    "error": row[7]
                }
                if job["status"] in ("queued", "running"):
                    return job, False
        c.execute("""
            INSERT OR REPLACE INTO jobs (id, job_type, status, idempotency_key, entity_id, stage, stage_data, error)
            VALUES (?, ?, 'queued', ?, ?, ?, ?, NULL)
        """, (job_id, job_type, idempotency_key, entity_id, stage, json.dumps({})))
    return {
        "id": job_id, "job_type": job_type, "status": "queued",
        "idempotency_key": idempotency_key, "entity_id": entity_id,
        "stage": stage, "stage_data": {}, "error": None
    }, True


def get_job(job_id: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT id, job_type, status, idempotency_key, entity_id, stage, stage_data, error FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        return None
    return {
        "id": row[0], "job_type": row[1], "status": row[2],
        "idempotency_key": row[3], "entity_id": row[4],
        "stage": row[5], "stage_data": json.loads(row[6]) if row[6] else {},
        "error": row[7]
    }


def update_job(job_id: str, status: str | None = None, stage: str | None = None, stage_data: dict | None = None, error: str | None = None) -> None:
    with _conn() as c:
        row = c.execute("SELECT status, stage, stage_data, error FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            return
        new_status = status or row[0]
        new_stage = stage or row[1]
        new_data = stage_data if stage_data is not None else (json.loads(row[2]) if row[2] else {})
        new_error = error if error is not None else row[3]
        c.execute("""
            UPDATE jobs SET status=?, stage=?, stage_data=?, error=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (new_status, new_stage, json.dumps(new_data), new_error, job_id))



def append_job_log(job_id: str, item: str | dict) -> None:
    with _conn() as c:
        c.execute("INSERT INTO job_logs (job_id, payload) VALUES (?, ?)", (job_id, json.dumps(item)))


def get_job_logs(job_id: str) -> list[str | dict]:
    with _conn() as c:
        rows = c.execute("SELECT payload FROM job_logs WHERE job_id=? ORDER BY id ASC", (job_id,)).fetchall()
    return [json.loads(r[0]) for r in rows]


def recover_interrupted_jobs() -> list[str]:
    """Finds jobs that were marked 'running' when the server stopped/restarted and marks them recovered."""
    recovered = []
    with _conn() as c:
        rows = c.execute("SELECT id, stage, stage_data FROM jobs WHERE status='running'").fetchall()
        for jid, stage, sdata in rows:
            c.execute("UPDATE jobs SET status='failed', error='Job interrupted by server restart (checkpoint saved)', updated_at=CURRENT_TIMESTAMP WHERE id=?", (jid,))
            recovered.append(jid)
    return recovered

