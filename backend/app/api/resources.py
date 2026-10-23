from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..repositories import collections as collections_repo
from ..repositories import resources as repo
from ..repositories import scans as scans_repo
from ..repositories import triage as triage_repo
from ..schemas.requests import ResourceIn, ResourcePatch, TriageIn
from ..services.scan_service import ScanError, run_scan, scan_payload
from .support import ApiError, body, db, int_arg, lang, not_found, paginated, settings

bp = Blueprint("resources", __name__)

USER_ERRORS = {"invalid_url", "blocked_host", "dns_error", "not_html", "too_large", "empty"}


def scan_error_response(exc: ScanError) -> ApiError:
    if exc.code == "not_found":
        return not_found("Ресурс")
    status = 422 if exc.code in USER_ERRORS else 502
    return ApiError(status, exc.code, exc.message, {"scan_id": exc.scan["id"] if exc.scan else None})


def _check_collection(collection_id: int | None) -> None:
    if collection_id is not None and collections_repo.get(db(), collection_id) is None:
        raise ApiError(422, "validation_error", "Коллекция не найдена", [{"field": "collection_id", "message": "Коллекция не найдена"}])


@bp.get("/resources")
def list_resources():
    raw_collection = request.args.get("collection_id")
    per_page = int_arg("per_page", 20, maximum=100)
    page = int_arg("page", 1)
    items, total = repo.search(
        db(),
        q=(request.args.get("q") or "").strip() or None,
        collection_id=int(raw_collection) if raw_collection and raw_collection.isdigit() else None,
        no_collection=raw_collection == "none",
        kind=request.args.get("kind") or None,
        band=request.args.get("band") or None,
        sort=request.args.get("sort", "updated"),
        order=request.args.get("order", "desc"),
        page=page,
        per_page=per_page,
    )
    return jsonify(paginated(items, total, page, per_page))


@bp.post("/resources")
def create_resource():
    data = body(ResourceIn)
    _check_collection(data.collection_id)
    resource = repo.create(db(), data.model_dump())
    response: dict = {"resource": resource}
    if request.args.get("scan") in ("1", "true"):
        try:
            scan = run_scan(db(), settings(), resource_id=resource["id"])
            response["scan"] = scan_payload(db(), scan, lang())
            response["resource"] = repo.get(db(), resource["id"])
        except ScanError as exc:
            response["scan_error"] = {"code": exc.code, "message": exc.message}
    return jsonify(response), 201


@bp.get("/resources/<int:resource_id>")
def get_resource(resource_id: int):
    resource = repo.get(db(), resource_id)
    if resource is None:
        raise not_found("Ресурс")
    if request.args.get("source") in ("1", "true"):
        resource["html"] = (repo.get_source(db(), resource_id) or {}).get("html")
    return jsonify(resource)


@bp.patch("/resources/<int:resource_id>")
def update_resource(resource_id: int):
    data = body(ResourcePatch)
    if repo.get(db(), resource_id) is None:
        raise not_found("Ресурс")
    fields = data.model_dump(exclude_unset=True)
    if "collection_id" in fields:
        _check_collection(fields["collection_id"])
    for key in ("title", "kind", "notes"):
        if key in fields and fields[key] is None:
            del fields[key]
    return jsonify(repo.update(db(), resource_id, fields))


@bp.delete("/resources/<int:resource_id>")
def delete_resource(resource_id: int):
    if not repo.delete(db(), resource_id):
        raise not_found("Ресурс")
    return "", 204


@bp.post("/resources/<int:resource_id>/scan")
def scan_resource(resource_id: int):
    try:
        scan = run_scan(db(), settings(), resource_id=resource_id)
    except ScanError as exc:
        raise scan_error_response(exc) from None
    return jsonify(scan_payload(db(), scan, lang())), 201


@bp.get("/resources/<int:resource_id>/latest")
def latest_scan(resource_id: int):
    resource = repo.get(db(), resource_id)
    if resource is None:
        raise not_found("Ресурс")
    if not resource["last_scan_id"]:
        raise ApiError(404, "no_scan", "Ресурс ещё не проверялся")
    scan = scans_repo.get(db(), resource["last_scan_id"])
    return jsonify(scan_payload(db(), scan, lang()))  # type: ignore[arg-type]


@bp.get("/resources/<int:resource_id>/scans")
def scan_history(resource_id: int):
    if repo.get(db(), resource_id) is None:
        raise not_found("Ресурс")
    items = scans_repo.history(db(), resource_id, limit=int_arg("limit", 50, maximum=200))
    return jsonify(items=items)


@bp.put("/resources/<int:resource_id>/triage/<fingerprint>")
def set_triage(resource_id: int, fingerprint: str):
    data = body(TriageIn)
    resource = repo.get(db(), resource_id)
    if resource is None:
        raise not_found("Ресурс")
    row = db().execute(
        "SELECT rule_id FROM findings WHERE scan_id = ? AND fingerprint = ? LIMIT 1", (resource["last_scan_id"], fingerprint)
    ).fetchone()
    if row is None:
        raise not_found("Замечание")
    return jsonify(triage_repo.set_status(db(), resource_id, fingerprint, row["rule_id"], data.status, data.note))
