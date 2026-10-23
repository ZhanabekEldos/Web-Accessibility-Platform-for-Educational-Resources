"""Демонстрационные данные: учебные страницы разного качества и история их улучшения."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from ..repositories import collections as collections_repo
from ..repositories import resources as resources_repo
from ..repositories import triage as triage_repo
from ..config import Settings
from .scan_service import run_scan

FIXTURES = Path(__file__).resolve().parent.parent / "data" / "fixtures"
COLLECTION = "Демо: учебные ресурсы"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _backdate(conn: sqlite3.Connection, scan_id: int, days_ago: int, resource_id: int) -> None:
    stamp = f"strftime('%Y-%m-%dT10:30:00Z', 'now', '-{int(days_ago)} days')"
    conn.execute(f"UPDATE scans SET created_at = {stamp} WHERE id = ?", (scan_id,))
    conn.execute(f"UPDATE resources SET last_scan_at = {stamp} WHERE id = ? AND last_scan_id = ?", (resource_id, scan_id))
    conn.commit()


def seed(conn: sqlite3.Connection, settings: Settings) -> dict[str, Any]:
    """Создаёт демо-коллекцию. Повторный вызов ничего не дублирует."""
    existing = collections_repo.get_by_name(conn, COLLECTION)
    if existing:
        return {"created": False, "collection_id": existing["id"]}
    collection = collections_repo.create(conn, COLLECTION, "Примеры страниц для знакомства с платформой")
    cid = collection["id"]

    chem = resources_repo.create(conn, {"collection_id": cid, "title": "Курс «Введение в химию»", "kind": "course", "html": _read("chem_course_v1.html"),
                                       "notes": "Главная страница курса. Исправляем по плану из отчёта."})
    first = run_scan(conn, settings, resource_id=chem["id"])
    _backdate(conn, first["id"], 21, chem["id"])
    # Отметим одно замечание как «в работе», чтобы показать триаж.
    for f in [f for f in _fingerprints(conn, first["id"]) if f["rule_id"] == "video-captions"][:1]:
        triage_repo.set_status(conn, chem["id"], f["fingerprint"], f["rule_id"], "in_progress", "Субтитры заказаны, ждём файл .vtt")

    resources_repo.update(conn, chem["id"], {"html": _read("chem_course_v2.html")})
    second = run_scan(conn, settings, resource_id=chem["id"])
    _backdate(conn, second["id"], 4, chem["id"])

    lecture = resources_repo.create(conn, {"collection_id": cid, "title": "Лекция 3. Пределы функций", "kind": "material", "html": _read("lecture_limits.html")})
    scan = run_scan(conn, settings, resource_id=lecture["id"])
    _backdate(conn, scan["id"], 9, lecture["id"])

    portal = resources_repo.create(conn, {"collection_id": cid, "title": "Портал колледжа — студентам", "kind": "portal", "html": _read("college_portal.html")})
    scan = run_scan(conn, settings, resource_id=portal["id"])
    _backdate(conn, scan["id"], 2, portal["id"])
    return {"created": True, "collection_id": cid}


def _fingerprints(conn: sqlite3.Connection, scan_id: int) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT rule_id, fingerprint FROM findings WHERE scan_id = ?", (scan_id,)).fetchall()
    return [dict(r) for r in rows]
