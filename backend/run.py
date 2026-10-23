"""Запуск для разработки: ``python run.py``. В продакшене используйте WSGI-сервер (gunicorn/waitress)."""
import os

from app.factory import create_app, start_scheduler

app = create_app()

if __name__ == "__main__":
    start_scheduler(app)
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8000")), threaded=True)
