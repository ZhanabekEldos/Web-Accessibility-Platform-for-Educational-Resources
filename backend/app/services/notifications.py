"""Уведомления: сравнение новой проверки с предыдущей и запись событий."""
from __future__ import annotations

import sqlite3
from typing import Any

from ..repositories import events as events_repo
from ..repositories import scans as scans_repo

SCORE_STEP = 5.0  # на сколько баллов должна измениться оценка, чтобы это стоило уведомления
_LEVEL_RANK = {None: 0, "A": 1, "AA": 2}


def after_scan(conn: sqlite3.Connection, resource_id: int | None, scan: dict[str, Any]) -> None:
    """Создаёт события по итогам проверки ресурса. Разовые проверки (без ресурса) не уведомляют."""
    if resource_id is None:
        return
    if scan["status"] != "ok":
        events_repo.add(conn, resource_id=resource_id, scan_id=scan["id"], type="scan_failed", severity="warning", data={"error": scan["error"]})
        conn.commit()
        return
    previous = scans_repo.previous_ok(conn, resource_id, scan["id"])
    if previous is None:
        return
    base = {"from": previous["score"], "to": scan["score"]}
    delta = (scan["score"] or 0) - (previous["score"] or 0)
    if delta <= -SCORE_STEP:
        events_repo.add(conn, resource_id=resource_id, scan_id=scan["id"], type="score_drop", severity="warning", data=base)
    elif delta >= SCORE_STEP:
        events_repo.add(conn, resource_id=resource_id, scan_id=scan["id"], type="score_rise", severity="success", data=base)
    old_rank, new_rank = _LEVEL_RANK.get(previous["level"], 0), _LEVEL_RANK.get(scan["level"], 0)
    if new_rank != old_rank:
        kind = "level_gained" if new_rank > old_rank else "level_lost"
        events_repo.add(conn, resource_id=resource_id, scan_id=scan["id"], type=kind, severity="success" if new_rank > old_rank else "warning",
                        data={"from": previous["level"], "to": scan["level"]})
    old_fp = {f["fingerprint"] for f in scans_repo.findings(conn, previous["id"]) if not f["needs_review"]}
    new_critical = [f for f in scans_repo.findings(conn, scan["id"]) if f["impact"] == "critical" and not f["needs_review"] and f["fingerprint"] not in old_fp]
    if new_critical:
        events_repo.add(conn, resource_id=resource_id, scan_id=scan["id"], type="new_critical", severity="warning",
                        data={"count": len(new_critical), "rules": sorted({f["rule_id"] for f in new_critical})[:5]})
    conn.commit()
