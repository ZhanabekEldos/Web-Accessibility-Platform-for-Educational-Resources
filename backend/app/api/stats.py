from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..repositories import stats as repo
from .support import db, int_arg

bp = Blueprint("stats", __name__)


@bp.get("/stats/overview")
def overview():
    raw = request.args.get("collection_id")
    collection_id = int(raw) if raw and raw.isdigit() else None
    return jsonify(repo.overview(db(), collection_id=collection_id, days=int_arg("days", 90, minimum=7, maximum=365)))
