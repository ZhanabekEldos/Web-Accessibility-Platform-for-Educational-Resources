CREATE TABLE collections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE resources (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER REFERENCES collections(id) ON DELETE SET NULL,
    title         TEXT NOT NULL,
    kind          TEXT NOT NULL DEFAULT 'page',
    url           TEXT,
    html          TEXT,
    notes         TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    last_scan_id  INTEGER,
    last_score    REAL,
    last_level    TEXT,
    last_scan_at  TEXT,
    CHECK (url IS NOT NULL OR html IS NOT NULL)
);
CREATE INDEX idx_resources_collection ON resources(collection_id);
CREATE INDEX idx_resources_score ON resources(last_score);

CREATE TABLE scans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id INTEGER REFERENCES resources(id) ON DELETE CASCADE,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    source      TEXT NOT NULL,
    url         TEXT,
    status      TEXT NOT NULL DEFAULT 'ok',
    error       TEXT,
    score       REAL,
    level       TEXT,
    violations  INTEGER NOT NULL DEFAULT 0,
    reviews     INTEGER NOT NULL DEFAULT 0,
    page_title  TEXT NOT NULL DEFAULT '',
    lang        TEXT,
    summary     TEXT NOT NULL DEFAULT '{}',
    duration_ms INTEGER NOT NULL DEFAULT 0,
    html_bytes  INTEGER NOT NULL DEFAULT 0,
    engine      TEXT NOT NULL DEFAULT ''
);
CREATE INDEX idx_scans_resource ON scans(resource_id, id DESC);
CREATE INDEX idx_scans_created ON scans(created_at);

CREATE TABLE findings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id      INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    rule_id      TEXT NOT NULL,
    impact       TEXT NOT NULL,
    level        TEXT NOT NULL,
    fingerprint  TEXT NOT NULL,
    selector     TEXT NOT NULL,
    snippet      TEXT NOT NULL,
    line         INTEGER,
    needs_review INTEGER NOT NULL DEFAULT 0,
    data         TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_findings_scan ON findings(scan_id);
CREATE INDEX idx_findings_rule ON findings(rule_id);

-- Статусы работы над замечаниями привязаны к ресурсу и «отпечатку» замечания,
-- поэтому переживают повторные проверки.
CREATE TABLE triage (
    resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    fingerprint TEXT NOT NULL,
    rule_id     TEXT NOT NULL,
    status      TEXT NOT NULL,
    note        TEXT NOT NULL DEFAULT '',
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (resource_id, fingerprint)
);
