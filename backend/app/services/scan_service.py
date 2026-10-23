"""Прикладная логика проверок: получение HTML, анализ, сохранение, представление результата."""
from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ..a11y.analyzer import EmptyDocumentError, analyze
from ..a11y.i18n import finding_message, rule_texts
from ..a11y.registry import REGISTRY
from ..a11y.wcag import CATALOG
from ..config import Settings
from ..db.database import connect
from ..repositories import resources as resources_repo
from ..repositories import scans as scans_repo
from ..repositories import triage as triage_repo
from . import notifications, recommendations
from .fetcher import FetchError, fetch_html


class ScanError(Exception):
    def __init__(self, code: str, message: str, scan: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.scan = scan


def run_scan(
    conn: sqlite3.Connection,
    settings: Settings,
    *,
    resource_id: int | None = None,
    url: str | None = None,
    html: str | None = None,
) -> dict[str, Any]:
    """Проверяет ресурс (по id), адрес или переданный HTML и сохраняет результат.

    Без ``resource_id`` результат сохраняется как разовая проверка (``resource_id = NULL``).
    """
    if resource_id is not None:
        source_row = resources_repo.get_source(conn, resource_id)
        if source_row is None:
            raise ScanError("not_found", "Ресурс не найден")
        url, html = source_row["url"], (None if source_row["url"] else source_row["html"])
    source = "html" if html is not None and not url else "url"
    try:
        if html is None:
            html = fetch_html(url or "", settings).html
        result = analyze(html)
    except FetchError as exc:
        failed = scans_repo.save_failure(conn, resource_id=resource_id, source=source, url=url, error=exc.message)
        _after(conn, resource_id, failed)
        raise ScanError(exc.code, exc.message, failed) from None
    except EmptyDocumentError:
        failed = scans_repo.save_failure(conn, resource_id=resource_id, source=source, url=url, error="Документ пуст")
        _after(conn, resource_id, failed)
        raise ScanError("empty", "Документ пуст", failed) from None
    scan = scans_repo.save(conn, result, resource_id=resource_id, source=source, url=url)
    _after(conn, resource_id, scan)
    return scan


def _after(conn: sqlite3.Connection, resource_id: int | None, scan: dict[str, Any]) -> None:
    """Побочные эффекты проверки ресурса: уведомления и сдвиг расписания."""
    if resource_id is None:
        return
    notifications.after_scan(conn, resource_id, scan)
    resources_repo.reschedule(conn, resource_id)


def run_batch(settings: Settings, resource_ids: list[int]) -> list[dict[str, Any]]:
    """Параллельно проверяет несколько ресурсов (у каждого потока своё соединение с БД)."""

    def work(rid: int) -> dict[str, Any]:
        conn = connect(settings.db_path)
        try:
            scan = run_scan(conn, settings, resource_id=rid)
            return {"resource_id": rid, "ok": True, "scan_id": scan["id"], "score": scan["score"], "level": scan["level"]}
        except ScanError as exc:
            return {"resource_id": rid, "ok": False, "code": exc.code, "error": exc.message}
        except Exception:  # noqa: BLE001
            return {"resource_id": rid, "ok": False, "code": "internal", "error": "Внутренняя ошибка проверки"}
        finally:
            conn.close()

    with ThreadPoolExecutor(max_workers=max(1, settings.batch_workers)) as pool:
        return list(pool.map(work, resource_ids))


# ------------------------------------------------------------------ представление
def present_finding(f: dict[str, Any], lang: str, triage_map: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    texts = rule_texts(f["rule_id"], lang)
    state = (triage_map or {}).get(f["fingerprint"])
    return {
        **f,
        "title": texts.get("title", f["rule_id"]),
        "message": finding_message(f["rule_id"], f["data"], f["needs_review"], lang),
        "triage": {"status": state["status"], "note": state["note"], "updated_at": state["updated_at"]} if state else {"status": "open", "note": "", "updated_at": None},
    }


def group_findings(findings: list[dict[str, Any]], lang: str) -> list[dict[str, Any]]:
    """Группирует замечания по правилам: заголовок, как исправить, критерии WCAG, замечания."""
    groups: dict[str, dict[str, Any]] = {}
    for f in findings:
        key = f["rule_id"]
        if key not in groups:
            rule = REGISTRY.get(key)
            texts = rule_texts(key, lang)
            groups[key] = {
                "rule_id": key,
                "title": texts.get("title", key),
                "fix": texts.get("fix", ""),
                "impact": f["impact"],
                "level": f["level"],
                "manual": bool(rule and rule.manual),
                "wcag": [CATALOG[sc].as_dict() for sc in (rule.wcag if rule else ()) if sc in CATALOG],
                "violations": 0,
                "reviews": 0,
                "findings": [],
            }
        g = groups[key]
        g["reviews" if f["needs_review"] else "violations"] += 1
        g["findings"].append(f)
    return list(groups.values())


def scan_payload(conn: sqlite3.Connection, scan: dict[str, Any], lang: str, *, with_findings: bool = True) -> dict[str, Any]:
    payload = dict(scan)
    if scan["status"] != "ok":
        payload.update(findings=[], groups=[], plan=[])
        return payload
    payload["truncated"] = scan["summary"].get("truncated", {})
    if with_findings:
        triage_map = triage_repo.for_resource(conn, scan["resource_id"]) if scan["resource_id"] else {}
        findings = [present_finding(f, lang, triage_map) for f in scans_repo.findings(conn, scan["id"])]
        payload["findings"] = findings
        payload["groups"] = group_findings(findings, lang)
    payload["plan"] = recommendations.build(scan["summary"], scan["score"], lang)
    previous = scans_repo.previous_ok(conn, scan["resource_id"], scan["id"]) if scan["resource_id"] else None
    payload["previous"] = {"id": previous["id"], "score": previous["score"], "created_at": previous["created_at"]} if previous else None
    return payload


def diff(conn: sqlite3.Connection, scan: dict[str, Any], base: dict[str, Any], lang: str) -> dict[str, Any]:
    """Сравнение двух проверок по «отпечаткам» замечаний: что исправлено, что появилось, что осталось."""
    current = {f["fingerprint"]: f for f in scans_repo.findings(conn, scan["id"]) if not f["needs_review"]}
    old = {f["fingerprint"]: f for f in scans_repo.findings(conn, base["id"]) if not f["needs_review"]}
    pick = lambda keys, source: [present_finding(source[k], lang) for k in keys]  # noqa: E731
    new_keys = [k for k in current if k not in old]
    fixed_keys = [k for k in old if k not in current]
    kept_keys = [k for k in current if k in old]
    return {
        "scan": {"id": scan["id"], "score": scan["score"], "created_at": scan["created_at"]},
        "base": {"id": base["id"], "score": base["score"], "created_at": base["created_at"]},
        "score_delta": round((scan["score"] or 0) - (base["score"] or 0), 1),
        "counts": {"new": len(new_keys), "fixed": len(fixed_keys), "persisting": len(kept_keys)},
        "new": pick(new_keys, current)[:200],
        "fixed": pick(fixed_keys, old)[:200],
    }
