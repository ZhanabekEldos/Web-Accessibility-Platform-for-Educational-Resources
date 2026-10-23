"""Ручной аудит: чек-лист с отметками по ресурсу и сводка прогресса."""
from __future__ import annotations

import sqlite3
from typing import Any

from ..a11y import checklist
from ..repositories import audit as audit_repo


def view(conn: sqlite3.Connection, resource_id: int, lang: str) -> dict[str, Any]:
    marks = audit_repo.for_resource(conn, resource_id)
    items = []
    for entry in checklist.catalog(lang):
        mark = marks.get(entry["id"])
        items.append({**entry, "status": mark["status"] if mark else None, "note": mark["note"] if mark else "", "updated_at": mark["updated_at"] if mark else None})
    counts = {"pass": 0, "fail": 0, "na": 0}
    for item in items:
        if item["status"]:
            counts[item["status"]] += 1
    done = sum(counts.values())
    return {"items": items, "progress": {"total": len(items), "done": done, **counts}}
