from __future__ import annotations

import sqlite3

from flask import Blueprint, Response, jsonify, request

from ..repositories import collections as repo
from ..repositories import resources as resources_repo
from ..services import reports
from ..schemas.requests import CollectionIn, CollectionPatch
from .support import ApiError, body, db, lang, not_found

bp = Blueprint("collections", __name__)


@bp.get("/collections")
def list_collections():
    return jsonify(items=repo.list_all(db()))


@bp.post("/collections")
def create_collection():
    data = body(CollectionIn)
    try:
        created = repo.create(db(), data.name, data.description)
    except sqlite3.IntegrityError:
        raise ApiError(409, "duplicate", "Коллекция с таким названием уже есть") from None
    return jsonify(created), 201


@bp.patch("/collections/<int:collection_id>")
def update_collection(collection_id: int):
    data = body(CollectionPatch)
    if repo.get(db(), collection_id) is None:
        raise not_found("Коллекция")
    try:
        updated = repo.update(db(), collection_id, data.model_dump(exclude_unset=True, exclude_none=True))
    except sqlite3.IntegrityError:
        raise ApiError(409, "duplicate", "Коллекция с таким названием уже есть") from None
    return jsonify(updated)


@bp.delete("/collections/<int:collection_id>")
def delete_collection(collection_id: int):
    with_resources = request.args.get("with_resources") in ("1", "true")
    if not repo.delete(db(), collection_id, with_resources=with_resources):
        raise not_found("Коллекция")
    return "", 204


@bp.get("/collections/<int:collection_id>/report")
def collection_report(collection_id: int):
    collection = repo.get(db(), collection_id)
    if collection is None:
        raise not_found("Коллекция")
    fmt = request.args.get("format", "html")
    if fmt not in ("html", "csv"):
        raise ApiError(400, "invalid_parameter", "format: html или csv")
    items, _ = resources_repo.search(db(), collection_id=collection_id, per_page=1000, sort="score", order="asc")
    current = lang()
    content = reports.collection_html(collection, items, current) if fmt == "html" else reports.collection_csv(collection, items, current)
    response = Response(content, mimetype="text/html" if fmt == "html" else "text/csv")
    response.headers["Content-Disposition"] = f'attachment; filename="collection-{collection_id}-report.{fmt}"'
    return response
