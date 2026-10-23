from __future__ import annotations

import sqlite3
from typing import Any

from ..a11y.analyzer import AnalysisResult
from ..a11y.registry import REGISTRY
from . import resources as resources_repo
from .common import dumps, loads, row_to_dict

_SCAN_COLUMNS = "id, resource_id, created_at, source, url, status, error, score, level, violations, reviews, page_title, lang, summary, duration_ms, html_bytes, engine"


def _prepare(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["summary"] = loads(item.get("summary"), {})
    return item


def save(
    conn: sqlite3.Connection,
    result: AnalysisResult,
    *,
    resource_id: int | None,
    source: str,
    url: str | None,
) -> dict[str, Any]:
    """Сохраняет результат проверки и замечания; обновляет «последнюю проверку» ресурса."""
    cur = conn.execute(
        """INSERT INTO scans(resource_id, source, url, status, score, level, violations, reviews, page_title, lang,
                             summary, duration_ms, html_bytes, engine)
           VALUES (?, ?, ?, 'ok', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            resource_id, source, url, result.score, result.level, result.summary["violations"], result.summary["reviews"],
            result.page_title, result.lang, dumps(result.summary), result.duration_ms, result.html_bytes, result.engine_version,
        ),
    )
    scan_id = cur.lastrowid
    rows = []
    for f in result.findings:
        rule = REGISTRY.get(f.rule_id)
        rows.append((scan_id, f.rule_id, rule.impact if rule else "minor", rule.level if rule else "BP",
                     f.fingerprint, f.selector, f.snippet, f.line, int(f.needs_review), dumps(f.data)))
    conn.executemany(
        "INSERT INTO findings(scan_id, rule_id, impact, level, fingerprint, selector, snippet, line, needs_review, data) VALUES (?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    scan = get(conn, scan_id)  # type: ignore[arg-type]
    if resource_id is not None:
        resources_repo.set_last_scan(conn, resource_id, scan)  # type: ignore[arg-type]
    conn.commit()
    return scan  # type: ignore[return-value]


def save_failure(conn: sqlite3.Connection, *, resource_id: int | None, source: str, url: str | None, error: str) -> dict[str, Any]:
    cur = conn.execute(
        "INSERT INTO scans(resource_id, source, url, status, error) VALUES (?, ?, ?, 'error', ?)",
        (resource_id, source, url, error[:500]),
    )
    conn.commit()
    return get(conn, cur.lastrowid)  # type: ignore[arg-type,return-value]


def get(conn: sqlite3.Connection, scan_id: int) -> dict[str, Any] | None:
    return _prepare(conn.execute(f"SELECT {_SCAN_COLUMNS} FROM scans WHERE id = ?", (scan_id,)).fetchone())


def history(conn: sqlite3.Connection, resource_id: int, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute(
        """SELECT id, resource_id, created_at, source, status, error, score, level, violations, reviews, duration_ms
           FROM scans WHERE resource_id = ? ORDER BY id DESC LIMIT ?""",
        (resource_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def previous_ok(conn: sqlite3.Connection, resource_id: int, before_id: int) -> dict[str, Any] | None:
    return _prepare(
        conn.execute(
            f"SELECT {_SCAN_COLUMNS} FROM scans WHERE resource_id = ? AND id < ? AND status = 'ok' ORDER BY id DESC LIMIT 1",
            (resource_id, before_id),
        ).fetchone()
    )


def findings(conn: sqlite3.Connection, scan_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """SELECT id, rule_id, impact, level, fingerprint, selector, snippet, line, needs_review, data
           FROM findings WHERE scan_id = ?
           ORDER BY CASE impact WHEN 'critical' THEN 0 WHEN 'serious' THEN 1 WHEN 'moderate' THEN 2 ELSE 3 END,
                    needs_review, rule_id, line, id""",
        (scan_id,),
    ).fetchall()
    out = []
    for r in rows:
        item = dict(r)
        item["needs_review"] = bool(item["needs_review"])
        item["data"] = loads(item["data"], {})
        out.append(item)
    return out


def delete(conn: sqlite3.Connection, scan_id: int) -> bool:
    row = row_to_dict(conn.execute("SELECT resource_id FROM scans WHERE id = ?", (scan_id,)).fetchone())
    if not row:
        return False
    conn.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
    if row["resource_id"] is not None:
        latest = conn.execute(
            "SELECT id, score, level, created_at FROM scans WHERE resource_id = ? AND status = 'ok' ORDER BY id DESC LIMIT 1",
            (row["resource_id"],),
        ).fetchone()
        if latest:
            resources_repo.set_last_scan(conn, row["resource_id"], dict(latest))
        else:
            conn.execute(
                "UPDATE resources SET last_scan_id=NULL,last_score=NULL,last_level=NULL,last_scan_at=NULL WHERE id=?",
                (row["resource_id"],),
            )
    conn.commit()
    return True
