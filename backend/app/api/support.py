"""Общие помощники API: ошибки, доступ к БД, разбор запросов, язык."""
from __future__ import annotations

import sqlite3
from typing import Any, TypeVar

from flask import current_app, g, request
from pydantic import BaseModel, ValidationError

from ..a11y.i18n import normalize_lang
from ..config import Settings
from ..db.database import connect

M = TypeVar("M", bound=BaseModel)


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details


def not_found(what: str = "Объект") -> ApiError:
    return ApiError(404, "not_found", f"{what} не найден")


def db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect(current_app.config["SETTINGS"].db_path)
    return g.db


def settings() -> Settings:
    return current_app.config["SETTINGS"]


def close_db(_exc: BaseException | None = None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def body(model: type[M]) -> M:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "invalid_json", "Ожидается JSON-объект в теле запроса")
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        details = [{"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"].removeprefix("Value error, ")} for e in exc.errors()]
        raise ApiError(422, "validation_error", details[0]["message"] if details else "Некорректные данные", details) from None


def lang() -> str:
    explicit = request.args.get("lang")
    if explicit:
        return normalize_lang(explicit)
    header = request.headers.get("Accept-Language", "")
    return normalize_lang(header.split(",")[0] if header else None)


def int_arg(name: str, default: int, *, minimum: int = 1, maximum: int = 100_000) -> int:
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    try:
        return max(minimum, min(maximum, int(raw)))
    except ValueError:
        raise ApiError(400, "invalid_parameter", f"Параметр {name} должен быть целым числом") from None


def paginated(items: list[Any], total: int, page: int, per_page: int) -> dict[str, Any]:
    return {"items": items, "total": total, "page": page, "per_page": per_page, "pages": max(1, -(-total // per_page))}
