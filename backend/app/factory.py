"""Фабрика приложения Flask."""
from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from .config import Settings
from .db.database import connect, migrate
from .api import academy, audit, collections, crawl, events, meta, resources, scans, stats, tools
from .api.support import ApiError, close_db


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or Settings()
    logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    static_dir = Path(settings.static_dir)
    app = Flask(__name__, static_folder=None)
    app.config["SETTINGS"] = settings
    app.config["JSON_AS_ASCII"] = False
    app.json.ensure_ascii = False  # type: ignore[attr-defined]
    app.json.sort_keys = False  # type: ignore[attr-defined]
    app.config["MAX_CONTENT_LENGTH"] = settings.max_html_bytes * 2

    conn = connect(settings.db_path)
    migrate(conn)
    conn.close()

    for module in (meta, collections, resources, scans, stats, tools, audit, events, academy, crawl):
        app.register_blueprint(module.bp, url_prefix="/api")
    app.teardown_appcontext(close_db)

    origins = {o.strip() for o in settings.cors_origins.split(",") if o.strip()}

    @app.after_request
    def add_headers(response):
        origin = request.headers.get("Origin")
        if origin and origin in origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept-Language"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response.headers["Vary"] = "Origin"
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.route("/api/<path:_any>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    def api_fallback(_any):
        if request.method == "OPTIONS":
            return "", 204  # CORS preflight
        raise ApiError(404, "not_found", "Маршрут не найден")

    @app.errorhandler(ApiError)
    def api_error(exc: ApiError):
        body = {"error": {"code": exc.code, "message": exc.message}}
        if exc.details is not None:
            body["error"]["details"] = exc.details
        return jsonify(body), exc.status

    @app.errorhandler(HTTPException)
    def http_error(exc: HTTPException):
        if request.path.startswith("/api/"):
            code = {404: "not_found", 405: "method_not_allowed", 413: "payload_too_large"}.get(exc.code or 500, "http_error")
            return jsonify(error={"code": code, "message": exc.description or exc.name}), exc.code or 500
        return exc

    @app.errorhandler(Exception)
    def unexpected(exc: Exception):
        app.logger.exception("Необработанная ошибка")
        return jsonify(error={"code": "internal", "message": "Внутренняя ошибка сервера"}), 500

    if static_dir.is_dir():

        @app.get("/", defaults={"path": ""})
        @app.get("/<path:path>")
        def spa(path: str):
            if path.startswith("api/"):
                raise ApiError(404, "not_found", "Маршрут не найден")
            target = static_dir / path
            if path and target.is_file():
                response = send_from_directory(static_dir, path)
                if path.startswith("assets/"):
                    response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
                return response
            response = send_from_directory(static_dir, "index.html")
            response.headers["Cache-Control"] = "no-cache"
            return response

    return app


def start_scheduler(app: Flask) -> None:
    """Запускает фоновые плановые проверки (вызывается из run.py и wsgi.py; в тестах не используется)."""
    from .services.scheduler import Scheduler

    settings: Settings = app.config["SETTINGS"]
    if settings.scheduler:
        Scheduler(settings, settings.scheduler_interval).start()
