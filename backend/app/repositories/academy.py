from __future__ import annotations

import sqlite3
from typing import Any


def all_progress(conn: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    rows = conn.execute("SELECT lesson_id, attempts, best_score, total, completed_at FROM academy_progress").fetchall()
    return {r["lesson_id"]: dict(r) for r in rows}


def record(conn: sqlite3.Connection, lesson_id: str, score: int, total: int, passed: bool) -> dict[str, Any]:
    conn.execute(
        """INSERT INTO academy_progress(lesson_id, attempts, best_score, total, completed_at)
           VALUES (?, 1, ?, ?, CASE WHEN ? THEN strftime('%Y-%m-%dT%H:%M:%fZ','now') END)
           ON CONFLICT(lesson_id) DO UPDATE SET
             attempts = attempts + 1,
             best_score = MAX(best_score, excluded.best_score),
             total = excluded.total,
             completed_at = COALESCE(completed_at, excluded.completed_at),
             updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')""",
        (lesson_id, score, total, int(passed)),
    )
    conn.commit()
    return all_progress(conn)[lesson_id]


def reset(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM academy_progress")
    conn.commit()
