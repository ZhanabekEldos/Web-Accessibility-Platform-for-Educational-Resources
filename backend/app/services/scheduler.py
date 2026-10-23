"""Плановые проверки: фоновый поток раз в минуту запускает проверки ресурсов, у которых наступил срок."""
from __future__ import annotations

import logging
import threading

from ..config import Settings
from ..db.database import connect
from ..repositories import resources as resources_repo
from .scan_service import ScanError, run_scan

log = logging.getLogger(__name__)


def run_due(settings: Settings, limit: int = 10) -> int:
    """Проверяет все просроченные ресурсы. Возвращает число обработанных. Удобно вызывать и из cron."""
    conn = connect(settings.db_path)
    try:
        ids = resources_repo.claim_due(conn, limit)
        for rid in ids:
            try:
                run_scan(conn, settings, resource_id=rid)
            except ScanError as exc:
                log.warning("Плановая проверка ресурса %s не удалась: %s", rid, exc.message)
            except Exception:  # noqa: BLE001
                log.exception("Плановая проверка ресурса %s: ошибка", rid)
        return len(ids)
    finally:
        conn.close()


class Scheduler:
    def __init__(self, settings: Settings, interval: int = 60) -> None:
        self.settings = settings
        self.interval = max(5, interval)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, name="accessedu-scheduler", daemon=True)
        self._thread.start()
        log.info("Планировщик проверок запущен (интервал %s с)", self.interval)

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                run_due(self.settings)
            except Exception:  # noqa: BLE001
                log.exception("Сбой планировщика")
