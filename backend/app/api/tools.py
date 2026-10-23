from __future__ import annotations

from flask import Blueprint, jsonify

from ..a11y import tools
from ..repositories import resources as resources_repo
from ..schemas.requests import ContrastIn, ReadabilityIn
from ..services.fetcher import FetchError, fetch_html
from .support import ApiError, body, db, not_found, settings

bp = Blueprint("tools", __name__)


@bp.post("/tools/contrast")
def contrast():
    data = body(ContrastIn)
    try:
        return jsonify(tools.contrast_report(data.fg, data.bg))
    except tools.ColorError as exc:
        label = "цвет текста" if exc.field == "fg" else "цвет фона"
        raise ApiError(422, "validation_error", f"Не удалось распознать {label}. Примеры: #1a1a1a, rgb(26 26 26), navy",
                       [{"field": exc.field, "message": f"Не удалось распознать {label}"}]) from None


@bp.post("/tools/readability")
def readability():
    data = body(ReadabilityIn)
    if data.resource_id is not None:
        source = resources_repo.get_source(db(), data.resource_id)
        if source is None:
            raise not_found("Ресурс")
        try:
            html = fetch_html(source["url"], settings()).html if source["url"] else source["html"]
        except FetchError as exc:
            raise ApiError(422, exc.code, exc.message) from None
        text = tools.text_from_html(html or "")
    elif data.html and data.html.strip():
        text = tools.text_from_html(data.html)
    else:
        text = data.text or ""
    return jsonify(tools.readability(text, data.lang))
