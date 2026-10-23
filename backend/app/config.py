"""Настройки приложения. Читаются из переменных окружения ``ACCESSEDU_*``."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

_TRUE = {"1", "true", "yes", "on"}


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(f"ACCESSEDU_{name}")
    return default if raw is None else raw.strip().lower() in _TRUE


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(f"ACCESSEDU_{name}", default))
    except ValueError:
        return default


@dataclass(frozen=True, slots=True)
class Settings:
    db_path: str = field(default_factory=lambda: os.environ.get("ACCESSEDU_DB_PATH", str(Path(__file__).resolve().parent.parent / "data" / "accessedu.sqlite3")))
    # Каталог собранного фронтенда; если существует, бэкенд отдаёт его сам.
    static_dir: str = field(default_factory=lambda: os.environ.get("ACCESSEDU_STATIC_DIR", str(Path(__file__).resolve().parents[2] / "frontend" / "dist")))
    cors_origins: str = field(default_factory=lambda: os.environ.get("ACCESSEDU_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"))
    # Разрешать проверку адресов во внутренних сетях (localhost, 10.x, 192.168.x). По умолчанию — нет (защита от SSRF).
    allow_private_hosts: bool = field(default_factory=lambda: _bool("ALLOW_PRIVATE_HOSTS", False))
    fetch_timeout: int = field(default_factory=lambda: _int("FETCH_TIMEOUT", 12))
    max_html_bytes: int = field(default_factory=lambda: _int("MAX_HTML_BYTES", 3 * 1024 * 1024))
    max_redirects: int = field(default_factory=lambda: _int("MAX_REDIRECTS", 5))
    batch_workers: int = field(default_factory=lambda: _int("BATCH_WORKERS", 4))
    batch_limit: int = field(default_factory=lambda: _int("BATCH_LIMIT", 25))
    # Фоновые плановые проверки (запускаются в run.py/wsgi.py, не в тестах).
    scheduler: bool = field(default_factory=lambda: _bool("SCHEDULER", True))
    scheduler_interval: int = field(default_factory=lambda: _int("SCHEDULER_INTERVAL", 60))
    user_agent: str = "AccessEduBot/1.0 (+accessibility audit)"
    debug: bool = field(default_factory=lambda: _bool("DEBUG", False))
