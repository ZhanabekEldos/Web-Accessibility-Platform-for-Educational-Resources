"""Тексты правил на разных языках.

Чтобы добавить язык, положите ``<код>.json`` в ``locales/`` по образцу ``en.json``:
``{rule_id: {title, message, fix, review?}}``. Недостающие правила берутся из английского.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

LOCALES_DIR = Path(__file__).parent / "locales"
FALLBACK = "en"


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "…"


def _stringify(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    return value


@lru_cache(maxsize=None)
def _load(lang: str) -> dict[str, dict[str, str]]:
    path = LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def available_languages() -> list[str]:
    return sorted(p.stem for p in LOCALES_DIR.glob("*.json"))


def normalize_lang(lang: str | None) -> str:
    code = (lang or FALLBACK).split("-")[0].split(",")[0].strip().lower()
    return code if code in available_languages() else FALLBACK


def rule_texts(rule_id: str, lang: str) -> dict[str, str]:
    base = _load(FALLBACK).get(rule_id, {})
    own = _load(normalize_lang(lang)).get(rule_id, {})
    return {**base, **own}


def finding_message(rule_id: str, data: dict[str, Any] | None, needs_review: bool, lang: str) -> str:
    texts = rule_texts(rule_id, lang)
    template = (texts.get("review") if needs_review else None) or texts.get("message") or rule_id
    values = _SafeDict({k: _stringify(v) for k, v in (data or {}).items()})
    try:
        return template.format_map(values)
    except (ValueError, IndexError, KeyError):
        return template
