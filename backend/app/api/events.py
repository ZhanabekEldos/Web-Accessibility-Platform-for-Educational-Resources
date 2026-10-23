from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..repositories import events as repo
from ..schemas.requests import EventsRead
from .support import body, db, int_arg, paginated

bp = Blueprint("events", __name__)


@bp.get("/events")
def list_events():
    per_page = int_arg("per_page", 30, maximum=100)
    page = int_arg("page", 1)
    items, total = repo.list_events(db(), unread_only=request.args.get("unread") in ("1", "true"), limit=per_page, offset=(page - 1) * per_page)
    return jsonify({**paginated(items, total, page, per_page), "unread": repo.unread_count(db())})


@bp.get("/events/unread-count")
def unread():
    return jsonify(unread=repo.unread_count(db()))


@bp.post("/events/read")
def mark_read():
    data = body(EventsRead)
    changed = repo.mark_read(db(), data.ids)
    return jsonify(changed=changed, unread=repo.unread_count(db()))


@bp.delete("/events")
def clear_events():
    repo.clear(db())
    return "", 204
