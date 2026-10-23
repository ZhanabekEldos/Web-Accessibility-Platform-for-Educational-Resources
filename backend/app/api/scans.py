from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from ..repositories import collections as collections_repo
from ..repositories import resources as resources_repo
from ..repositories import scans as repo
from ..schemas.requests import BatchIn, ScanIn
from ..services import reports
from ..services.scan_service import ScanError, diff, run_batch, run_scan, scan_payload
from .resources import scan_error_response
from .support import ApiError, body, db, int_arg, lang, not_found, settings

bp = Blueprint("scans", __name__)


@bp.post("/scans")
def create_scan():
    data = body(ScanIn)
    resource_id = data.resource_id
    if data.save_as:
        if data.save_as.collection_id is not None and collections_repo.get(db(), data.save_as.collection_id) is None:
            raise ApiError(422, "validation_error", "Коллекция не найдена")
        resource = resources_repo.create(
            db(), {**data.save_as.model_dump(), "url": data.url, "html": None if data.url else data.html}
        )
        resource_id = resource["id"]
    try:
        if resource_id is not None:
            scan = run_scan(db(), settings(), resource_id=resource_id)
        else:
            scan = run_scan(db(), settings(), url=data.url, html=None if data.url else data.html)
    except ScanError as exc:
        raise scan_error_response(exc) from None
    return jsonify(scan_payload(db(), scan, lang())), 201


@bp.post("/scans/batch")
def batch_scan():
    data = body(BatchIn)
    if data.collection_id is not None:
        if collections_repo.get(db(), data.collection_id) is None:
            raise not_found("Коллекция")
        ids = resources_repo.ids_in_collection(db(), data.collection_id)
    else:
        ids = list(dict.fromkeys(data.resource_ids or []))
    limit = settings().batch_limit
    if len(ids) > limit:
        raise ApiError(422, "batch_too_large", f"За один раз можно проверить не более {limit} ресурсов")
    results = run_batch(settings(), ids)
    return jsonify(results=results, ok=sum(1 for r in results if r["ok"]), failed=sum(1 for r in results if not r["ok"]))


def _get_scan(scan_id: int) -> dict:
    scan = repo.get(db(), scan_id)
    if scan is None:
        raise not_found("Проверка")
    return scan


@bp.get("/scans/<int:scan_id>")
def get_scan(scan_id: int):
    return jsonify(scan_payload(db(), _get_scan(scan_id), lang()))


@bp.delete("/scans/<int:scan_id>")
def delete_scan(scan_id: int):
    if not repo.delete(db(), scan_id):
        raise not_found("Проверка")
    return "", 204


@bp.get("/scans/<int:scan_id>/diff")
def scan_diff(scan_id: int):
    scan = _get_scan(scan_id)
    base_id = request.args.get("base")
    if base_id and base_id.isdigit():
        base = repo.get(db(), int(base_id))
    elif scan["resource_id"]:
        base = repo.previous_ok(db(), scan["resource_id"], scan["id"])
    else:
        base = None
    if base is None or base["status"] != "ok" or scan["status"] != "ok":
        raise ApiError(404, "no_base", "Нет предыдущей проверки для сравнения")
    return jsonify(diff(db(), scan, base, lang()))


_MIME = {"json": "application/json", "csv": "text/csv", "html": "text/html"}


@bp.get("/scans/<int:scan_id>/export")
def export_scan(scan_id: int):
    scan = _get_scan(scan_id)
    if scan["status"] != "ok":
        raise ApiError(422, "scan_failed", "У неудачной проверки нет данных для экспорта")
    fmt = request.args.get("format", "json")
    if fmt not in _MIME:
        raise ApiError(400, "invalid_parameter", "format: json, csv или html")
    current = lang()
    payload = scan_payload(db(), scan, current)
    title = None
    if scan["resource_id"]:
        resource = resources_repo.get(db(), scan["resource_id"])
        title = resource["title"] if resource else None
    if fmt == "json":
        content = reports.to_json(payload)
    elif fmt == "csv":
        content = reports.to_csv(payload, current)
    else:
        content = reports.to_html(payload, title, current)
    response = Response(content, mimetype=_MIME[fmt])
    response.headers["Content-Disposition"] = f'attachment; filename="accessibility-report-{scan_id}.{fmt}"'
    return response
