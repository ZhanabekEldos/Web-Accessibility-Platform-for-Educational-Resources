from __future__ import annotations

import sqlite3
from typing import Any


def for_resource(conn: sqlite3.Connection, resource_id: int) -> dict[str, dict[str, Any]]:
    rows = conn.execute("SELECT item_id, status, note, updated_at FROM audit_items WHERE resource_id = ?", (resource_id,)).fetchall()
    return {r["item_id"]: dict(r) for r in rows}


def set_status(conn: sqlite3.Connection, resource_id: int, item_id: str, status: str | None, note: str) -> None:
    """``status=None`` сбрасывает пункт в «не проверено»."""
    if status is None:
        conn.execute("DELETE FROM audit_items WHERE resource_id = ? AND item_id = ?", (resource_id, item_id))
    else:
        conn.execute(
            """INSERT INTO audit_items(resource_id, item_id, status, note) VALUES (?, ?, ?, ?)
               ON CONFLICT(resource_id, item_id) DO UPDATE SET status = excluded.status, note = excluded.note,
               updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')""",
            (resource_id, item_id, status, note),
        )
    conn.commit()
