from __future__ import annotations

import sqlite3
from typing import Any

from ..a11y.registry import IMPACTS, PRINCIPLES
from .common import loads


def overview(conn: sqlite3.Connection, *, collection_id: int | None = None, days: int = 90) -> dict[str, Any]:
    scope_sql = "WHERE r.collection_id = :cid" if collection_id is not None else ""
    params = {"cid": collection_id}

    totals = conn.execute(
        f"""SELECT COUNT(*) AS resources,
                   SUM(r.last_score IS NOT NULL) AS scanned,
                   ROUND(AVG(r.last_score), 1) AS avg_score,
                   SUM(r.last_score >= 90) AS good,
                   SUM(r.last_score >= 70 AND r.last_score < 90) AS fair,
                   SUM(r.last_score < 70) AS poor,
                   SUM(r.last_level = 'AA') AS level_aa,
                   SUM(r.last_level = 'A') AS level_a
            FROM resources r {scope_sql}""",
        params,
    ).fetchone()
    totals_d = {k: (totals[k] or 0) for k in totals.keys()}
    totals_d["avg_score"] = totals["avg_score"]
    totals_d["unscanned"] = totals_d["resources"] - totals_d["scanned"]
    totals_d["level_none"] = totals_d["scanned"] - totals_d["level_aa"] - totals_d["level_a"]

    # Нарушения по серьёзности и правилам — только по последним проверкам ресурсов.
    join = "FROM findings f JOIN resources r ON r.last_scan_id = f.scan_id" + (" AND r.collection_id = :cid" if collection_id is not None else "")
    by_impact = {i: 0 for i in IMPACTS}
    for row in conn.execute(f"SELECT f.impact, COUNT(*) n {join} WHERE f.needs_review = 0 GROUP BY f.impact", params):
        by_impact[row["impact"]] = row["n"]
    top_rules = [
        dict(r)
        for r in conn.execute(
            f"""SELECT f.rule_id, f.impact, f.level, COUNT(*) AS violations, COUNT(DISTINCT r.id) AS resources
                {join} WHERE f.needs_review = 0 GROUP BY f.rule_id ORDER BY resources DESC, violations DESC LIMIT 8""",
            params,
        )
    ]

    principle_sum = {p: [0.0, 0] for p in PRINCIPLES}
    for row in conn.execute(f"SELECT s.summary FROM resources r JOIN scans s ON s.id = r.last_scan_id {scope_sql}", params):
        for p, value in (loads(row["summary"], {}).get("principles") or {}).items():
            if p in principle_sum and value is not None:
                principle_sum[p][0] += value
                principle_sum[p][1] += 1
    by_principle = {p: (round(s / n, 1) if n else None) for p, (s, n) in principle_sum.items()}

    trend_scope = "AND s.resource_id IN (SELECT id FROM resources WHERE collection_id = :cid)" if collection_id is not None else "AND s.resource_id IS NOT NULL"
    trend = [
        dict(r)
        for r in conn.execute(
            f"""SELECT substr(s.created_at, 1, 10) AS day, ROUND(AVG(s.score), 1) AS avg_score, COUNT(*) AS scans
                FROM scans s WHERE s.status = 'ok' AND s.created_at >= date('now', :since) {trend_scope}
                GROUP BY day ORDER BY day""",
            {**params, "since": f"-{int(days)} days"},
        )
    ]

    worst = [
        dict(r)
        for r in conn.execute(
            f"""SELECT r.id, r.title, r.last_score, r.last_level, s.violations FROM resources r
                JOIN scans s ON s.id = r.last_scan_id {scope_sql.replace('WHERE', 'WHERE') if scope_sql else ''}
                ORDER BY r.last_score ASC, s.violations DESC LIMIT 5""",
            params,
        )
    ]

    improvement = conn.execute(
        f"""WITH ranked AS (
                SELECT s.resource_id, s.score,
                       ROW_NUMBER() OVER (PARTITION BY s.resource_id ORDER BY s.id ASC) AS first_rn,
                       ROW_NUMBER() OVER (PARTITION BY s.resource_id ORDER BY s.id DESC) AS last_rn,
                       COUNT(*) OVER (PARTITION BY s.resource_id) AS cnt
                FROM scans s JOIN resources r ON r.id = s.resource_id
                WHERE s.status = 'ok' {('AND r.collection_id = :cid') if collection_id is not None else ''}
            )
            SELECT COUNT(DISTINCT resource_id) AS tracked,
                   ROUND(AVG(CASE WHEN last_rn = 1 THEN score END) - AVG(CASE WHEN first_rn = 1 THEN score END), 1) AS avg_delta
            FROM ranked WHERE cnt >= 2""",
        params,
    ).fetchone()

    return {
        "totals": totals_d,
        "by_impact": by_impact,
        "by_principle": by_principle,
        "top_rules": top_rules,
        "trend": trend,
        "worst": worst,
        "improvement": {"tracked": improvement["tracked"] or 0, "avg_delta": improvement["avg_delta"]},
    }
