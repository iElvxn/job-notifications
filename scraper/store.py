"""SQLite-backed store of job IDs we've already notified about."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "seen_jobs.db"


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS seen_jobs (id TEXT PRIMARY KEY)")
    conn.commit()
    return conn


def get_seen_ids(conn):
    rows = conn.execute("SELECT id FROM seen_jobs").fetchall()
    return {row[0] for row in rows}


def mark_seen(conn, job_ids):
    conn.executemany(
        "INSERT OR IGNORE INTO seen_jobs (id) VALUES (?)",
        [(job_id,) for job_id in job_ids],
    )
    conn.commit()


def is_empty(conn):
    row = conn.execute("SELECT COUNT(*) FROM seen_jobs").fetchone()
    return row[0] == 0
