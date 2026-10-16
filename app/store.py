"""Tiny SQLite document store. One JSON blob per person / date / run."""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager

from .config import DB_PATH, DATA_DIR
from .models import DateRecord, Person

_lock = threading.Lock()


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


def set_meta(k: str, v) -> None:
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (k, json.dumps(v)))


def get_meta(k: str, default=None):
    with _conn() as c:
        row = c.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
    return json.loads(row[0]) if row else default
