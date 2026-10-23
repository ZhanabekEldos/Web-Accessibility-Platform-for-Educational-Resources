from __future__ import annotations

from flask import Blueprint, jsonify

from ..repositories import collections as collections_repo
from ..repositories import resources as resources_repo
from ..schemas.requests import CrawlDiscoverIn, CrawlImportIn
from ..services.crawler import discover, normalize
from ..services.fetcher import FetchError, validate_url
from ..services.scan_service import run_batch
from .support import ApiError, body, db, not_found, settings

bp = Blueprint("crawl", __name__)

ERROR_STATUS = {"invalid_url": 422, "blocked_host": 422, "dns_error": 422, "not_html": 422, "too_large": 422}


@bp.post("/crawl/discover")
def crawl_discover():
    """Шаг 1: найти страницы сайта (ничего не сохраняется), чтобы пользователь выбрал нужные."""
    data = body(CrawlDiscoverIn)
    try:
        pages, root = discover(data.url, settings(), limit=data.limit, depth=data.depth)
    except FetchError as exc:
        raise ApiError(ERROR_STATUS.get(exc.code, 502), exc.code, exc.message) from None
    existing = {r["url"] for r in db().execute("SELECT url FROM resources WHERE url IS NOT NULL")}
    return jsonify(root=root, pages=[{"url": p.url, "title": p.title, "exists": p.url in existing} for p in pages])


@bp.post("/crawl/import")
def crawl_import():
    """Шаг 2: добавить выбранные страницы как ресурсы (повторы пропускаются) и при желании проверить их."""
    data = body(CrawlImportIn)
    if len(data.pages) > settings().batch_limit and data.scan:
        raise ApiError(422, "batch_too_large", f"За один раз можно проверить не более {settings().batch_limit} страниц")
    for page in data.pages:
        try:
            validate_url(page.url, allow_private=settings().allow_private_hosts)
        except FetchError as exc:
            raise ApiError(422, exc.code, f"{page.url}: {exc.message}") from None

    collection_id = data.collection_id
    if collection_id is not None and collections_repo.get(db(), collection_id) is None:
        raise not_found("Коллекция")
    if data.collection_name:
        found = collections_repo.get_by_name(db(), data.collection_name)
        collection_id = found["id"] if found else collections_repo.create(db(), data.collection_name)["id"]

    by_url = {r["url"]: r["id"] for r in db().execute("SELECT id, url FROM resources WHERE url IS NOT NULL")}
    created, skipped, ids = 0, 0, []
    for page in data.pages:
        url = normalize(page.url)
        if url in by_url:
            skipped += 1
            ids.append(by_url[url])
            continue
        title = page.title or url
        res = resources_repo.create(db(), {"title": title[:200], "kind": data.kind, "url": url, "collection_id": collection_id, "schedule": data.schedule})
        by_url[url] = res["id"]
        ids.append(res["id"])
        created += 1
    result = {"collection_id": collection_id, "created": created, "skipped": skipped, "resource_ids": ids}
    if data.scan:
        results = run_batch(settings(), ids)
        result.update(results=results, ok=sum(1 for r in results if r["ok"]), failed=sum(1 for r in results if not r["ok"]))
    return jsonify(result), 201
