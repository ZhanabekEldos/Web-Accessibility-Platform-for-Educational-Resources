# AccessEdu: a platform for assessing and improving the web accessibility of educational resources

*Русская версия: [README.ru.md](README.ru.md)*

AccessEdu checks course pages, learning materials and institutional portals against WCAG 2.2 and gives each a score from 0 to 100.
It explains every violation in Russian or English, builds a fix plan ("what to fix first and how much the score will rise")
and keeps a scan history so progress is visible over time.

* **Backend:** Python 3.11+, Flask, Pydantic v2, SQLite, BeautifulSoup.
* **Frontend:** React 19, built with esbuild, no heavy dependencies.

## Quick start

```bash
make install   # pip install + npm install
make run       # build the frontend and serve everything at http://localhost:8000
```

Without `make`:

```bash
cd frontend && npm install && npm run build
cd ../backend && pip install -r requirements.txt && python run.py
```

Open http://localhost:8000. On the empty dashboard click **"Load demo data"**: three sample course pages appear,
with scan history, trends and issue statuses.

Development mode (the frontend rebuilds on change, `/api` is proxied to the backend):

```bash
make dev        # backend on :8000, UI at http://localhost:5173
```

Docker: `docker compose up --build` → http://localhost:8000 (data lives in the `accessedu-data` volume).

Tests: `make test` (105 tests: rules, CSS contrast, scoring, API, SSRF protection, tools, audit, site crawling, scheduler, learning).

## Features

| Feature | Where |
|---|---|
| Scan by URL or pasted HTML (including pages behind a login) | "Check" |
| Resources and collections, search, filters, sorting, bulk scanning | "Resources", "Collections" |
| Score 0–100, WCAG level (A / AA), scores per POUR principle | resource page |
| Fix plan with a forecast of the score gain | "Fix plan" tab |
| Issue workflow statuses (in progress, fixed, won't fix, false positive) and notes, kept between scans | "Findings" tab |
| Scan history and comparison: fixed / new / persisting | "History" tab |
| Report export: HTML (self-contained), CSV (for Excel), JSON | "Download report" |
| Rule library: explanation, "bad / good" example, links to WCAG criteria | "Rules" |
| Whole site: discover pages by links, pick the ones you need, add them to a collection and bulk-scan | "Check" → "Whole site" |
| Manual audit: 22-item checklist (keyboard, screen reader, captions, formulas, etc.) with marks and notes | "Manual audit" tab |
| Accessibility statement (ru/en): text built from scan and audit results, HTML/Markdown; SVG badge with the score for your site | "Statement" tab |
| Scheduled scans (daily / weekly) and notifications: score dropped or rose, new critical issues, level lost, scan failed | "About" tab, "Notifications" |
| Contrast calculator that suggests the nearest passing color | "Tools" |
| Text readability analysis (Flesch index, long sentences and words) for a page, a resource or pasted text | "Tools" |
| Learning: 6 short lessons for teachers with quizzes and progress tracking | "Learn" |
| Collection report (HTML, CSV) | "Collections" |
| Accessibility settings for the interface itself: theme (including high contrast), text size, animations, language | "Settings" |

## How the score works

* Only **applicable automated** rules count: if a page has no video, the caption rules do not affect the score.
* A rule's weight depends on its impact: critical 10, serious 7, moderate 3, minor 1.
* A rule with no violations earns full points; with violations it earns partial points (at most 50%), fewer the larger the share of failing elements.
  The score therefore grows as issues are fixed, but a page with a critical error cannot get "almost 100".
* "Needs manual review" items (audio without a transcript, text over a background image, etc.) are not part of the score and are shown separately.
* A WCAG level ("A", "AA") is awarded when there are no violations at that level. **Automated testing covers only part of the criteria**,
  so results should be complemented by manual testing with a keyboard and a screen reader; the interface says so too.

Code: `backend/app/a11y/scoring.py` (the formulas, about 70 lines).

## Architecture

```
accessedu/
├── backend/
│   ├── app/
│   │   ├── a11y/                 # core: the checking engine, independent of the web and the DB
│   │   │   ├── rules/            # rules by group (images, forms, links, aria, color, …)
│   │   │   ├── registry.py       # registry, @rule decorator, finding fingerprints
│   │   │   ├── document.py       # HTML wrapper: accessible name, hidden state, CSS path
│   │   │   ├── css.py            # mini CSS engine for contrast (cascade, var(), colors)
│   │   │   ├── scoring.py        # score and WCAG level formulas
│   │   │   ├── analyzer.py       # analyze(html) → result
│   │   │   ├── wcag.py           # WCAG 2.2 criteria catalog
│   │   │   ├── tools.py          # contrast with color suggestions, text readability
│   │   │   ├── checklist.py      # manual audit items
│   │   │   ├── i18n.py, locales/ # rule texts: ru.json, en.json
│   │   ├── api/                  # Flask blueprints: meta, collections, resources, scans, stats, tools, audit, events, academy, crawl
│   │   ├── repositories/         # SQL: collections, resources, scans, triage, statistics, audit, events, academy
│   │   ├── services/             # URL fetcher (SSRF), scans, site crawler, notifications, scheduler, statement, reports, demo
│   │   ├── data/academy.py       # lessons and quizzes (ru/en)
│   │   ├── schemas/requests.py   # input validation (Pydantic)
│   │   ├── db/                   # SQLite connection and migrations (migrations/NNN_*.sql)
│   │   ├── config.py, factory.py # settings from the environment, application factory
│   └── tests/
└── frontend/
    └── src/
        ├── pages/                # Dashboard, Resources, ResourceDetail, Check, Collections, Rules, Tools, Academy, Notifications
        ├── components/           # ScanReport, Charts, Dialog, Tabs, AuditView, StatementView, CrawlForm, ui (buttons, fields, score mark)
        ├── i18n/                 # ru.js, en.js: flat dictionaries
        ├── styles/app.css        # design system: tokens, themes, components
        ├── api.js, router.jsx, prefs.jsx, hooks.js
```

Layers depend only "downwards": `api → services → repositories → db`. The `a11y` package knows nothing about Flask or SQLite,
so the engine can be used on its own (CLI, CI, another framework): `from app.a11y.analyzer import analyze`.

## Extending the platform

### Add a rule

1. Write a function in any module under `backend/app/a11y/rules/` (or add a new module and import it in `rules/__init__.py`):

   ```python
   @rule(
       id="table-caption", wcag=["1.3.1"], level="BP", impact="minor", principle="perceivable",
       tags=["tables"],
       bad="<table><tr><th>A</th></tr></table>",
       good="<table><caption>Grades</caption><tr><th>A</th></tr></table>",
   )
   def table_caption(doc: Document, report: RuleReport) -> None:
       for table in doc.find_all("table"):
           report.checked()              # the rule applies to this element
           if not table.find("caption"):
               report.fail(table)        # or report.review(table) for "check manually"
   ```

2. Add texts to `locales/ru.json` and `locales/en.json`: `{"title": …, "message": …, "fix": …}`
   (`message` may use `{fields}` passed via `report.fail(el, data={...})`).
3. Run `make test`. The tests check that the rule flags its "bad" example, passes its "good" one and has texts in every language.

A new WCAG criterion goes into `a11y/wcag.py`. Scoring, reports, filters, the "Rules" page and the fix plan pick the rule up automatically.

### Add a language

* Rules: `backend/app/a11y/locales/kk.json` (modelled on `en.json`; anything missing falls back to English).
* Interface: `frontend/src/i18n/kk.js` (modelled on `en.js`), then a line in `i18n/index.jsx` (`DICTS`, `LANGUAGES`) and in `prefs.jsx`.
* Kazakh plural forms match English: `{ one, other }`.

### Add a manual audit item or a lesson

* Audit item: an `Item(...)` entry in `backend/app/a11y/checklist.py` (principle, WCAG criteria, ru/en texts).
* Lesson: a dictionary in `backend/app/data/academy.py` (ru/en texts and questions; the correct answer is stored once and never sent to the client). The `test_workflow` tests check that translations stay consistent.
* Notification event: rules live in `services/notifications.py`; the text is an `event.<type>` key in the interface dictionaries.

### Change the database schema

Add a file `backend/app/db/migrations/003_name.sql`; it runs once at startup. Do not edit existing migrations.

### Add a page or an endpoint

* API: a module in `backend/app/api/` with a `Blueprint`, registered in `factory.py`. Validate requests with a schema from `schemas/requests.py` and raise errors via `ApiError`.
* Interface: a page in `frontend/src/pages/`, a route and menu item in `app.jsx`, texts in both dictionaries.

## Settings (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `ACCESSEDU_DB_PATH` | `backend/data/accessedu.sqlite3` | database file |
| `ACCESSEDU_STATIC_DIR` | `frontend/dist` | directory with the built frontend |
| `ACCESSEDU_ALLOW_PRIVATE_HOSTS` | `false` | allow scanning internal-network addresses (intranet) |
| `ACCESSEDU_FETCH_TIMEOUT` | `12` | page download timeout, seconds |
| `ACCESSEDU_MAX_HTML_BYTES` | `3145728` | maximum page size |
| `ACCESSEDU_BATCH_WORKERS`, `ACCESSEDU_BATCH_LIMIT` | `4`, `25` | bulk-scan parallelism and limit |
| `ACCESSEDU_SCHEDULER`, `ACCESSEDU_SCHEDULER_INTERVAL` | `true`, `60` | background scheduled scans and polling period, seconds |
| `ACCESSEDU_CORS_ORIGINS` | `http://localhost:5173,…` | allowed origins in development mode |

## Security

* **SSRF.** The fetcher (`services/fetcher.py`) allows only http/https, rejects credentials in the URL, checks the IP **at connection time**
  (protection against DNS rebinding) and after every redirect, and limits size, time and number of redirects. Internal networks
  (localhost, 10.x, 192.168.x, 169.254.x, etc.) are blocked by default. For an intranet, enable `ACCESSEDU_ALLOW_PRIVATE_HOSTS`.
* Reports: HTML is escaped; CSV is protected against formula injection (`=`, `+`, `-`, `@`).
* Input is strictly validated (extra fields are rejected) and all SQL is parameterized.

> The platform has no user authentication: it is meant to run inside an organization. To expose it to the internet,
> put a reverse proxy with authentication in front of it or add a user layer (a convenient hook is `before_request` in `factory.py`).

## Known limitations and ideas

* The engine analyzes **HTML and CSS without running JavaScript**: content rendered by scripts is checked from the source code.
  For single-page apps, paste the HTML after rendering (from the browser inspector). A natural next step is a headless browser (Playwright) as a second HTML source.
* Contrast is computed from inline styles and `<style>` blocks; external stylesheets, `@media`, `opacity` and `color-mix()` are not taken into account
  (in such cases the platform does not raise false violations).
* PDF/DOCX checking is not implemented: such links go to "check manually".
* The scheduler runs inside the server process (`run.py`, `wsgi.py`); with several gunicorn processes a scan is never duplicated (a resource is claimed atomically). For cron, call `app.services.scheduler.run_due(settings)`.
* Site crawling follows links to HTML pages on the same host (depth 1–2, up to 50 pages) and does not run JavaScript.
* Readability: the Flesch index is computed for Russian (Oborneva's adaptation) and English; other languages are not scored.
* Ideas: roles and authentication, email notifications, PDF/DOCX checks, headless-browser scanning, collection comparison, a Kazakh interface.
