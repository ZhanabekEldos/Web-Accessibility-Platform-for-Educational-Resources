from __future__ import annotations

import sqlite3
from typing import Any

from .common import dumps, loads


def add(conn: sqlite3.Connection, *, resource_id: int | None, scan_id: int | None, type: str, severity: str, data: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO events(resource_id, scan_id, type, severity, data) VALUES (?, ?, ?, ?, ?)",
        (resource_id, scan_id, type, severity, dumps(data)),
    )


def list_events(conn: sqlite3.Connection, *, unread_only: bool = False, limit: int = 50, offset: int = 0) -> tuple[list[dict[str, Any]], int]:
    where = "WHERE e.read_at IS NULL" if unread_only else ""
    total = conn.execute(f"SELECT COUNT(*) FROM events e {where}").fetchone()[0]
    rows = conn.execute(
        f"""SELECT e.id, e.resource_id, r.title AS resource_title, e.scan_id, e.type, e.severity, e.data, e.created_at, e.read_at
            FROM events e LEFT JOIN resources r ON r.id = e.resource_id {where}
            ORDER BY e.id DESC LIMIT ? OFFSET ?""",
        (limit, offset),
    ).fetchall()
    items = []
    for r in rows:
        item = dict(r)
        item["data"] = loads(item["data"], {})
        item["read"] = item.pop("read_at") is not None
        items.append(item)
    return items, total


def unread_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM events WHERE read_at IS NULL").fetchone()[0]


def mark_read(conn: sqlite3.Connection, ids: list[int] | None) -> int:
    if ids is None:
        cur = conn.execute("UPDATE events SET read_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE read_at IS NULL")
    else:
        marks = ",".join("?" * len(ids)) or "NULL"
        cur = conn.execute(
            f"UPDATE events SET read_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE read_at IS NULL AND id IN ({marks})", ids
        )
    conn.commit()
    return cur.rowcount


def clear(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM events")
    conn.commit()
