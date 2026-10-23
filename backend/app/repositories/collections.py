from __future__ import annotations

import sqlite3
from typing import Any

from .common import row_to_dict


def list_all(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT c.*, COUNT(r.id) AS resources_count,
               ROUND(AVG(r.last_score), 1) AS avg_score,
               SUM(CASE WHEN r.last_score IS NOT NULL THEN 1 ELSE 0 END) AS scanned_count
        FROM collections c LEFT JOIN resources r ON r.collection_id = c.id
        GROUP BY c.id ORDER BY c.name COLLATE NOCASE
        """
    ).fetchall()
    return [dict(r) for r in rows]


def get(conn: sqlite3.Connection, collection_id: int) -> dict[str, Any] | None:
    return row_to_dict(conn.execute("SELECT * FROM collections WHERE id = ?", (collection_id,)).fetchone())


def create(conn: sqlite3.Connection, name: str, description: str = "") -> dict[str, Any]:
    cur = conn.execute("INSERT INTO collections(name, description) VALUES (?, ?)", (name, description))
    conn.commit()
    return get(conn, cur.lastrowid)  # type: ignore[arg-type,return-value]


def update(conn: sqlite3.Connection, collection_id: int, fields: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {k: v for k, v in fields.items() if k in ("name", "description")}
    if allowed:
        sets = ", ".join(f"{k} = ?" for k in allowed)
        conn.execute(f"UPDATE collections SET {sets} WHERE id = ?", (*allowed.values(), collection_id))
        conn.commit()
    return get(conn, collection_id)


def delete(conn: sqlite3.Connection, collection_id: int, *, with_resources: bool = False) -> bool:
    if with_resources:
        conn.execute("DELETE FROM resources WHERE collection_id = ?", (collection_id,))
    cur = conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
    conn.commit()
    return cur.rowcount > 0


def get_by_name(conn: sqlite3.Connection, name: str) -> dict[str, Any] | None:
    return row_to_dict(conn.execute("SELECT * FROM collections WHERE name = ?", (name,)).fetchone())
