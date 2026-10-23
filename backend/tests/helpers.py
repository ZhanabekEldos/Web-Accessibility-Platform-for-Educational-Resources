from __future__ import annotations

import os
import shutil
import tempfile
import unittest

from app.config import Settings
from app.db.database import connect
from app.factory import create_app


class ApiTestCase(unittest.TestCase):
    """База для тестов API: отдельная временная БД на каждый тест."""

    settings_overrides: dict = {}

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.settings = Settings(db_path=os.path.join(self.tmp, "test.sqlite3"), static_dir=os.path.join(self.tmp, "none"), **self.settings_overrides)
        self.app = create_app(self.settings)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def raw_db(self):
        """Отдельное соединение с БД теста (закрывается автоматически)."""
        conn = connect(self.settings.db_path)
        self.addCleanup(conn.close)
        return conn

    def make_resource(self, **overrides) -> dict:
        payload = {"title": "Тест", "html": "<html lang='ru'><head><title>T</title></head><body><main><h1>Привет</h1><img src='a.png'></main></body></html>"}
        payload.update(overrides)
        resp = self.client.post("/api/resources", json=payload)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))
        return resp.json["resource"]
