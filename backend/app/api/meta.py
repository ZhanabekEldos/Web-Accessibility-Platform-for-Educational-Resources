from __future__ import annotations

from flask import Blueprint, jsonify

from .. import __version__
from ..a11y.analyzer import ENGINE_VERSION
from ..a11y.i18n import available_languages, rule_texts
from ..a11y.registry import IMPACTS, LEVELS, PRINCIPLES, REGISTRY
from ..a11y.wcag import CATALOG, WCAG_VERSION
from ..services import demo
from .support import db, lang, settings

bp = Blueprint("meta", __name__)


@bp.get("/health")
def health():
    db().execute("SELECT 1")
    return jsonify(status="ok", version=__version__, engine=ENGINE_VERSION)


@bp.get("/meta")
def meta():
    return jsonify(
        version=__version__,
        engine=ENGINE_VERSION,
        wcag_version=WCAG_VERSION,
        languages=available_languages(),
        impacts=IMPACTS,
        levels=LEVELS,
        principles=PRINCIPLES,
        rules_total=len(REGISTRY),
        allow_private_hosts=settings().allow_private_hosts,
    )


@bp.get("/rules")
def rules():
    current = lang()
    items = []
    for rule in REGISTRY:
        texts = rule_texts(rule.id, current)
        items.append(
            {
                "id": rule.id,
                "title": texts.get("title", rule.id),
                "description": texts.get("message", ""),
                "fix": texts.get("fix", ""),
                "impact": rule.impact,
                "level": rule.level,
                "principle": rule.principle,
                "tags": list(rule.tags),
                "manual": rule.manual,
                "wcag": [CATALOG[sc].as_dict() for sc in rule.wcag],
                "bad": rule.bad,
                "good": rule.good,
            }
        )
    return jsonify(items=items, total=len(items))


@bp.post("/demo/seed")
def seed_demo():
    result = demo.seed(db(), settings())
    return jsonify(result), (201 if result["created"] else 200)
