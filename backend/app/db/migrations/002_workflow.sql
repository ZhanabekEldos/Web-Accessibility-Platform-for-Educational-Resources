-- Расписание повторных проверок, уведомления, ручной аудит и прогресс обучения.

ALTER TABLE resources ADD COLUMN schedule TEXT NOT NULL DEFAULT 'off';
ALTER TABLE resources ADD COLUMN next_run_at TEXT;
CREATE INDEX idx_resources_next_run ON resources(next_run_at);

-- Ручной аудит: чек-лист того, что автоматика проверить не может.
CREATE TABLE audit_items (
    resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    item_id     TEXT NOT NULL,
    status      TEXT NOT NULL,           -- pass | fail | na
    note        TEXT NOT NULL DEFAULT '',
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (resource_id, item_id)
);

-- Уведомления: падение оценки, новые критические ошибки, сбой проверки и т. п.
CREATE TABLE events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id INTEGER REFERENCES resources(id) ON DELETE CASCADE,
    scan_id     INTEGER REFERENCES scans(id) ON DELETE SET NULL,
    type        TEXT NOT NULL,
    severity    TEXT NOT NULL DEFAULT 'info',   -- info | success | warning
    data        TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    read_at     TEXT
);
CREATE INDEX idx_events_created ON events(created_at DESC);
CREATE INDEX idx_events_unread ON events(read_at);

-- Прогресс по урокам академии.
CREATE TABLE academy_progress (
    lesson_id    TEXT PRIMARY KEY,
    attempts     INTEGER NOT NULL DEFAULT 0,
    best_score   INTEGER NOT NULL DEFAULT 0,
    total        INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    updated_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
