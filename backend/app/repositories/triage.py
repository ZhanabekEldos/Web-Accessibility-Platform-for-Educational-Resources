from __future__ import annotations

import sqlite3
from typing import Any

STATUSES = ("open", "in_progress", "fixed", "wontfix", "false_positive")


def for_resource(conn: sqlite3.Connection, resource_id: int) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        "SELECT fingerprint, rule_id, status, note, updated_at FROM triage WHERE resource_id = ?", (resource_id,)
    ).fetchall()
    return {r["fingerprint"]: dict(r) for r in rows}


def set_status(conn: sqlite3.Connection, resource_id: int, fingerprint: str, rule_id: str, status: str, note: str = "") -> dict[str, Any]:
    if status == "open" and not note:
        conn.execute("DELETE FROM triage WHERE resource_id = ? AND fingerprint = ?", (resource_id, fingerprint))
        conn.commit()
        return {"fingerprint": fingerprint, "rule_id": rule_id, "status": "open", "note": "", "updated_at": None}
    conn.execute(
        """INSERT INTO triage(resource_id, fingerprint, rule_id, status, note) VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(resource_id, fingerprint) DO UPDATE SET status = excluded.status, note = excluded.note,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')""",
        (resource_id, fingerprint, rule_id, status, note),
    )
    conn.commit()
    row = conn.execute("SELECT fingerprint, rule_id, status, note, updated_at FROM triage WHERE resource_id=? AND fingerprint=?", (resource_id, fingerprint)).fetchone()
    return dict(row)
