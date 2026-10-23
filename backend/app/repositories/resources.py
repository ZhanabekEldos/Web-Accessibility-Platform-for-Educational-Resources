from __future__ import annotations

import sqlite3
from typing import Any

from datetime import datetime, timedelta, timezone

from .common import like, row_to_dict

SCHEDULES = {"off": None, "daily": timedelta(days=1), "weekly": timedelta(days=7)}


def now_iso(delta: timedelta | None = None) -> str:
    moment = datetime.now(timezone.utc) + (delta or timedelta())
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def next_run_after(schedule: str) -> str | None:
    delta = SCHEDULES.get(schedule)
    return now_iso(delta) if delta else None

SORTABLE = {
    "title": "r.title COLLATE NOCASE",
    "score": "r.last_score",
    "updated": "r.updated_at",
    "created": "r.created_at",
    "scanned": "r.last_scan_at",
}
_SELECT = """
    SELECT r.id, r.collection_id, c.name AS collection_name, r.title, r.kind, r.url,
           (r.html IS NOT NULL) AS has_html, r.notes, r.created_at, r.updated_at,
           r.last_scan_id, r.last_score, r.last_level, r.last_scan_at, r.schedule, r.next_run_at,
           s.violations AS last_violations, s.reviews AS last_reviews, s.status AS last_status
    FROM resources r
    LEFT JOIN collections c ON c.id = r.collection_id
    LEFT JOIN scans s ON s.id = r.last_scan_id
"""


def _prepare(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["has_html"] = bool(item["has_html"])
    return item


def search(
    conn: sqlite3.Connection,
    *,
    q: str | None = None,
    collection_id: int | None = None,
    no_collection: bool = False,
    kind: str | None = None,
    band: str | None = None,
    sort: str = "updated",
    order: str = "desc",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    where: list[str] = []
    params: list[Any] = []
    if q:
        where.append("(r.title LIKE ? ESCAPE '\\' OR r.url LIKE ? ESCAPE '\\')")
        params += [like(q), like(q)]
    if collection_id is not None:
        where.append("r.collection_id = ?")
        params.append(collection_id)
    elif no_collection:
        where.append("r.collection_id IS NULL")
    if kind:
        where.append("r.kind = ?")
        params.append(kind)
    bands = {"good": "r.last_score >= 90", "fair": "r.last_score >= 70 AND r.last_score < 90",
             "poor": "r.last_score < 70", "unscanned": "r.last_score IS NULL"}
    if band in bands:
        where.append(bands[band])
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    total = conn.execute(f"SELECT COUNT(*) FROM resources r{clause}", params).fetchone()[0]
    column = SORTABLE.get(sort, SORTABLE["updated"])
    direction = "ASC" if order.lower() == "asc" else "DESC"
    # Непроверенные ресурсы всегда в конце списка.
    rows = conn.execute(
        f"{_SELECT}{clause} ORDER BY ({column} IS NULL), {column} {direction}, r.id DESC LIMIT ? OFFSET ?",
        [*params, per_page, (page - 1) * per_page],
    ).fetchall()
    return [_prepare(r) for r in rows], total


def get(conn: sqlite3.Connection, resource_id: int) -> dict[str, Any] | None:
    row = conn.execute(f"{_SELECT} WHERE r.id = ?", (resource_id,)).fetchone()
    return _prepare(row) if row else None


def get_source(conn: sqlite3.Connection, resource_id: int) -> dict[str, Any] | None:
    return row_to_dict(conn.execute("SELECT id, url, html, title FROM resources WHERE id = ?", (resource_id,)).fetchone())


def create(conn: sqlite3.Connection, data: dict[str, Any]) -> dict[str, Any]:
    schedule = data.get("schedule") or "off"
    cur = conn.execute(
        "INSERT INTO resources(collection_id, title, kind, url, html, notes, schedule, next_run_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (data.get("collection_id"), data["title"], data.get("kind", "page"), data.get("url"), data.get("html"), data.get("notes", ""),
         schedule, next_run_after(schedule)),
    )
    conn.commit()
    return get(conn, cur.lastrowid)  # type: ignore[arg-type,return-value]


def update(conn: sqlite3.Connection, resource_id: int, fields: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {k: v for k, v in fields.items() if k in ("collection_id", "title", "kind", "url", "html", "notes", "schedule")}
    if "schedule" in allowed:
        allowed["next_run_at"] = next_run_after(allowed["schedule"])
    if allowed:
        sets = ", ".join(f"{k} = ?" for k in allowed)
        conn.execute(
            f"UPDATE resources SET {sets}, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = ?",
            (*allowed.values(), resource_id),
        )
        conn.commit()
    return get(conn, resource_id)


def delete(conn: sqlite3.Connection, resource_id: int) -> bool:
    cur = conn.execute("DELETE FROM resources WHERE id = ?", (resource_id,))
    conn.commit()
    return cur.rowcount > 0


def set_last_scan(conn: sqlite3.Connection, resource_id: int, scan: dict[str, Any]) -> None:
    conn.execute(
        "UPDATE resources SET last_scan_id = ?, last_score = ?, last_level = ?, last_scan_at = ? WHERE id = ?",
        (scan["id"], scan["score"], scan["level"], scan["created_at"], resource_id),
    )


def ids_in_collection(conn: sqlite3.Connection, collection_id: int) -> list[int]:
    return [r[0] for r in conn.execute("SELECT id FROM resources WHERE collection_id = ? ORDER BY id", (collection_id,))]


def reschedule(conn: sqlite3.Connection, resource_id: int) -> None:
    """Сдвигает следующий запуск после проверки (ручной или плановой)."""
    row = conn.execute("SELECT schedule FROM resources WHERE id = ?", (resource_id,)).fetchone()
    if row and row["schedule"] != "off":
        conn.execute("UPDATE resources SET next_run_at = ? WHERE id = ?", (next_run_after(row["schedule"]), resource_id))
        conn.commit()


def claim_due(conn: sqlite3.Connection, limit: int = 10) -> list[int]:
    """Выбирает ресурсы с наступившим сроком и «занимает» их (несколько процессов не запустят одну проверку дважды)."""
    now = now_iso()
    due = conn.execute(
        "SELECT id, schedule FROM resources WHERE schedule != 'off' AND next_run_at IS NOT NULL AND next_run_at <= ? ORDER BY next_run_at LIMIT ?",
        (now, limit),
    ).fetchall()
    claimed = []
    for row in due:
        cur = conn.execute(
            "UPDATE resources SET next_run_at = ? WHERE id = ? AND next_run_at <= ?",
            (next_run_after(row["schedule"]), row["id"], now),
        )
        if cur.rowcount == 1:
            claimed.append(row["id"])
    conn.commit()
    return claimed
