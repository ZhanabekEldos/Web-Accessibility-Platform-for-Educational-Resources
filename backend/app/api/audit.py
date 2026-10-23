from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from ..a11y import checklist
from ..a11y.wcag import WCAG_VERSION
from ..repositories import audit as audit_repo
from ..repositories import resources as resources_repo
from ..repositories import scans as scans_repo
from ..schemas.requests import AuditIn, StatementQuery
from ..services import audit_service, badge, statement
from ..services.scan_service import group_findings, present_finding
from .support import ApiError, body, db, lang, not_found

bp = Blueprint("audit", __name__)


def _resource(resource_id: int) -> dict:
    resource = resources_repo.get(db(), resource_id)
    if resource is None:
        raise not_found("Ресурс")
    return resource


@bp.get("/resources/<int:resource_id>/audit")
def get_audit(resource_id: int):
    _resource(resource_id)
    return jsonify(audit_service.view(db(), resource_id, lang()))


@bp.put("/resources/<int:resource_id>/audit/<item_id>")
def set_audit(resource_id: int, item_id: str):
    _resource(resource_id)
    if item_id not in checklist.BY_ID:
        raise not_found("Пункт чек-листа")
    data = body(AuditIn)
    audit_repo.set_status(db(), resource_id, item_id, data.status, data.note)
    return jsonify(audit_service.view(db(), resource_id, lang()))


@bp.get("/resources/<int:resource_id>/statement")
def get_statement(resource_id: int):
    resource = _resource(resource_id)
    try:
        query = StatementQuery.model_validate({k: request.args.get(k, "") for k in ("organization", "contact")})
    except ValueError:
        raise ApiError(422, "validation_error", "Слишком длинное значение") from None
    fmt = request.args.get("format", "json")
    if fmt not in ("json", "md", "html"):
        raise ApiError(400, "invalid_parameter", "format: json, md или html")
    current = lang()
    scan = scans_repo.get(db(), resource["last_scan_id"]) if resource["last_scan_id"] else None
    groups = []
    if scan and scan["status"] == "ok":
        groups = group_findings([present_finding(f, current) for f in scans_repo.findings(db(), scan["id"])], current)
    doc = statement.build(
        lang=current, resource=resource, scan=scan, groups=groups, audit=audit_service.view(db(), resource_id, current),
        organization=query.organization, contact=query.contact, wcag_version=WCAG_VERSION,
    )
    if fmt == "json":
        return jsonify(doc)
    if fmt == "md":
        response = Response(statement.to_markdown(doc), mimetype="text/markdown")
        response.headers["Content-Disposition"] = 'attachment; filename="accessibility-statement.md"'
    else:
        response = Response(statement.to_html(doc), mimetype="text/html")
        response.headers["Content-Disposition"] = 'attachment; filename="accessibility-statement.html"'
    return response


@bp.get("/resources/<int:resource_id>/badge.svg")
def get_badge(resource_id: int):
    resource = _resource(resource_id)
    label = "доступность" if lang() == "ru" else "accessibility"
    response = Response(badge.render(label, resource["last_score"], resource["last_level"]), mimetype="image/svg+xml")
    response.headers["Cache-Control"] = "public, max-age=300"
    return response
