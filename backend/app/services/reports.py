"""Экспорт результатов проверки: JSON, CSV, самодостаточный HTML-отчёт."""
from __future__ import annotations

import csv
import io
import json
from html import escape
from typing import Any

IMPACT_RU = {"critical": "Критично", "serious": "Серьёзно", "moderate": "Умеренно", "minor": "Незначительно"}
IMPACT_EN = {"critical": "Critical", "serious": "Serious", "moderate": "Moderate", "minor": "Minor"}

_I18N = {
    "ru": {
        "title": "Отчёт о доступности", "score": "Оценка", "level": "Соответствие WCAG", "violations": "Нарушения",
        "reviews": "Проверить вручную", "date": "Дата проверки", "fix": "Как исправить", "none": "не достигнуто",
        "found": "Найдено", "line": "строка", "plan": "План исправлений", "gain": "прирост оценки",
        "empty": "Нарушений не найдено.", "note": "Автоматическая проверка покрывает лишь часть критериев WCAG; результат дополняйте ручной проверкой.",
        "headers": ["Серьёзность", "Правило", "Критерии WCAG", "Требуется ручная проверка", "Сообщение", "Селектор", "Строка", "Фрагмент", "Статус"],
        "yes": "да", "no": "нет",
    },
    "en": {
        "title": "Accessibility report", "score": "Score", "level": "WCAG conformance", "violations": "Violations",
        "reviews": "Needs review", "date": "Scan date", "fix": "How to fix", "none": "not met",
        "found": "Found", "line": "line", "plan": "Fix plan", "gain": "score gain",
        "empty": "No violations found.", "note": "Automated testing covers only part of WCAG; complement it with manual review.",
        "headers": ["Impact", "Rule", "WCAG criteria", "Needs review", "Message", "Selector", "Line", "Snippet", "Status"],
        "yes": "yes", "no": "no",
    },
}


def _t(lang: str) -> dict[str, Any]:
    return _I18N.get(lang, _I18N["en"])


def to_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def _csv_safe(value: Any) -> str:
    """Защита от CSV-инъекций: значения, начинающиеся с формульных символов, экранируются."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def to_csv(payload: dict[str, Any], lang: str) -> str:
    t = _t(lang)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(t["headers"])
    wcag_by_rule = {g["rule_id"]: ", ".join(c["id"] for c in g["wcag"]) for g in payload.get("groups", [])}
    for f in payload.get("findings", []):
        writer.writerow(
            [_csv_safe(v) for v in (
                f["impact"], f["rule_id"], wcag_by_rule.get(f["rule_id"], ""), t["yes"] if f["needs_review"] else t["no"],
                f["message"], f["selector"], f["line"], f["snippet"], f["triage"]["status"],
            )]
        )
    return "﻿" + out.getvalue()  # BOM — чтобы Excel открыл кириллицу


def to_html(payload: dict[str, Any], resource_title: str | None, lang: str) -> str:
    t = _t(lang)
    impacts = IMPACT_RU if lang == "ru" else IMPACT_EN
    e = escape
    level = payload.get("level") or t["none"]
    score = payload.get("score")
    title = resource_title or payload.get("page_title") or payload.get("url") or t["title"]

    groups_html = []
    for g in payload.get("groups", []):
        items = "".join(
            f'<li><div>{e(f["message"])}</div><code>{e(f["selector"])}'
            f'{(" · " + t["line"] + " " + str(f["line"])) if f["line"] else ""}</code><pre>{e(f["snippet"])}</pre></li>'
            for f in g["findings"][:50]
        )
        wcag = ", ".join(c["id"] for c in g["wcag"])
        count = g["violations"] or g["reviews"]
        groups_html.append(
            f'<section class="g {e(g["impact"])}"><h3><span class="b">{e(impacts[g["impact"]])}</span> {e(g["title"])}'
            f' <small>{e(wcag)} · {t["found"]}: {count}</small></h3>'
            f'<p class="fix"><strong>{t["fix"]}:</strong> {e(g["fix"])}</p><ul>{items}</ul></section>'
        )
    plan_html = "".join(
        f'<li>{e(p["title"])} <small>+{p["gain"]} {t["gain"]}</small></li>' for p in payload.get("plan", [])[:8] if p["gain"] > 0
    )
    return f"""<!doctype html>
<html lang="{e(lang)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(t["title"])} — {e(title)}</title>
<style>
body{{font:16px/1.55 system-ui,sans-serif;margin:0;color:#1b1f2a;background:#f6f7fb}}
main{{max-width:60rem;margin:0 auto;padding:2rem 1rem}}
header{{background:#fff;border-radius:16px;padding:1.5rem;box-shadow:0 1px 3px #0002;margin-bottom:1.5rem}}
h1{{margin:0 0 .25rem;font-size:1.6rem}} .meta{{color:#4a5160}}
.kpi{{display:flex;gap:2rem;flex-wrap:wrap;margin-top:1rem}} .kpi b{{display:block;font-size:2rem}}
.g{{background:#fff;border-radius:12px;padding:1rem 1.25rem;margin-bottom:1rem;border-left:6px solid #888}}
.g.critical{{border-color:#b3261e}} .g.serious{{border-color:#c25b00}} .g.moderate{{border-color:#8a6d00}} .g.minor{{border-color:#4a5160}}
.g h3{{margin:.2rem 0;font-size:1.05rem}} small{{color:#4a5160;font-weight:400}}
.b{{display:inline-block;font-size:.75rem;padding:.1rem .5rem;border-radius:99px;background:#eef0f6;margin-right:.4rem}}
li{{margin:.6rem 0}} code{{font-size:.8rem;color:#4a5160}} pre{{background:#f1f3f9;padding:.5rem .75rem;border-radius:8px;overflow:auto;font-size:.8rem;margin:.25rem 0}}
.note{{color:#4a5160;font-size:.9rem}}
</style></head><body><main>
<header><h1>{e(t["title"])}</h1><div class="meta">{e(title)}{(" · " + e(payload["url"])) if payload.get("url") else ""} · {e(t["date"])}: {e(str(payload.get("created_at", "")))}</div>
<div class="kpi"><div><b>{score if score is not None else "—"}</b>{t["score"]}</div><div><b>{e(str(level))}</b>{t["level"]}</div>
<div><b>{payload.get("violations", 0)}</b>{t["violations"]}</div><div><b>{payload.get("reviews", 0)}</b>{t["reviews"]}</div></div></header>
{('<section class="g"><h3>' + t["plan"] + '</h3><ol>' + plan_html + '</ol></section>') if plan_html else ""}
{"".join(groups_html) or '<p>' + t["empty"] + '</p>'}
<p class="note">{t["note"]}</p></main></body></html>"""


# ------------------------------------------------------------------ отчёт по коллекции
_COLLECTION = {
    "ru": {"title": "Отчёт по коллекции", "avg": "Средняя оценка", "count": "Ресурсов", "scanned": "Проверено", "good": "Оценка 90+",
           "headers": ["Ресурс", "Адрес", "Оценка", "Уровень WCAG", "Нарушения", "Проверить вручную", "Дата проверки"], "worst": "Сначала — самые проблемные ресурсы."},
    "en": {"title": "Collection report", "avg": "Average score", "count": "Resources", "scanned": "Scanned", "good": "Score 90+",
           "headers": ["Resource", "URL", "Score", "WCAG level", "Violations", "Needs review", "Scan date"], "worst": "The most problematic resources come first."},
}


def _sorted_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda r: (r["last_score"] is None, r["last_score"] if r["last_score"] is not None else 0))


def collection_csv(collection: dict[str, Any], items: list[dict[str, Any]], lang: str) -> str:
    t = _COLLECTION.get(lang, _COLLECTION["en"])
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(t["headers"])
    for r in _sorted_rows(items):
        writer.writerow([_csv_safe(v) for v in (r["title"], r["url"] or "", r["last_score"], r["last_level"] or "", r["last_violations"], r["last_reviews"], r["last_scan_at"])])
    return "﻿" + out.getvalue()


def collection_html(collection: dict[str, Any], items: list[dict[str, Any]], lang: str) -> str:
    t = _COLLECTION.get(lang, _COLLECTION["en"])
    e = escape
    scored = [r["last_score"] for r in items if r["last_score"] is not None]
    avg = f"{sum(scored) / len(scored):.1f}" if scored else "—"
    good = sum(1 for s in scored if s >= 90)
    rows = "".join(
        f'<tr><td>{e(r["title"])}</td><td>{e(r["url"] or "")}</td><td>{"—" if r["last_score"] is None else round(r["last_score"])}</td>'
        f'<td>{e(r["last_level"] or "—")}</td><td>{r["last_violations"] if r["last_violations"] is not None else "—"}</td>'
        f'<td>{r["last_reviews"] if r["last_reviews"] is not None else "—"}</td></tr>'
        for r in _sorted_rows(items)
    )
    heads = "".join(f"<th scope=\"col\">{e(h)}</th>" for h in t["headers"][:6])
    return f"""<!doctype html>
<html lang="{e(lang)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(t["title"])} — {e(collection["name"])}</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;margin:0;background:#f6f7fb;color:#1b1f2a}}main{{max-width:64rem;margin:0 auto;padding:2rem 1rem}}
.kpi{{display:flex;gap:2rem;flex-wrap:wrap;margin:1rem 0}}.kpi b{{display:block;font-size:2rem}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden}}th,td{{text-align:left;padding:.6rem .8rem;border-bottom:1px solid #e3e6ef;vertical-align:top}}th{{background:#eef0f6}}
td:nth-child(2){{word-break:break-all;color:#4a5160;font-size:.85rem}}</style></head><body><main>
<h1>{e(t["title"])}: {e(collection["name"])}</h1><p>{e(collection.get("description") or "")}</p>
<div class="kpi"><div><b>{avg}</b>{t["avg"]}</div><div><b>{len(items)}</b>{t["count"]}</div><div><b>{len(scored)}</b>{t["scanned"]}</div><div><b>{good}</b>{t["good"]}</div></div>
<p>{t["worst"]}</p><table><thead><tr>{heads}</tr></thead><tbody>{rows}</tbody></table></main></body></html>"""
