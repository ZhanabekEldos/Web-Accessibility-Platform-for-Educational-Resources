# Многоэтапная сборка: фронтенд → бэкенд, отдающий готовую статику.
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn
COPY backend/ ./
COPY --from=web /web/dist /app/static
ENV ACCESSEDU_STATIC_DIR=/app/static ACCESSEDU_DB_PATH=/data/accessedu.sqlite3
VOLUME /data
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "wsgi:app"]
