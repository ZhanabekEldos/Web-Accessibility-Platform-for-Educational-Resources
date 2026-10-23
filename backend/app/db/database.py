"""Подключение к SQLite и простой накатчик миграций.

Миграции — файлы ``migrations/NNN_name.sql``; применяются по порядку один раз.
Чтобы изменить схему, добавьте новый файл, существующие не правьте.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def connect(path: str) -> sqlite3.Connection:
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def migrate(conn: sqlite3.Connection) -> list[str]:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    done = {r["name"] for r in conn.execute("SELECT name FROM schema_migrations")}
    applied: list[str] = []
    for file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if not re.fullmatch(r"\d{3}_[\w-]+\.sql", file.name) or file.name in done:
            continue
        conn.executescript(file.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO schema_migrations(name) VALUES (?)", (file.name,))
        conn.commit()
        applied.append(file.name)
    return applied
