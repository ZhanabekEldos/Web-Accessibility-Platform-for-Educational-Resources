"""Генератор «Заявления о доступности» по результатам автоматической проверки и ручного аудита."""
from __future__ import annotations

from datetime import date
from html import escape
from typing import Any

T = {
    "ru": {
        "title": "Заявление о доступности",
        "intro": "{org} стремится обеспечить доступность ресурса «{res}» для всех пользователей, включая людей с нарушениями зрения, слуха, моторики и когнитивными особенностями.",
        "standard": "Стандарт",
        "standard_text": "Ориентир — Руководство по обеспечению доступности веб-контента WCAG {ver}, уровень AA.",
        "status": "Статус соответствия",
        "status_full": "Ресурс соответствует WCAG {ver} уровня AA по результатам автоматической проверки и ручного аудита.",
        "status_partial": "Ресурс соответствует требованиям WCAG {ver} частично.",
        "status_none": "Ресурс ещё не проверялся, поэтому о соответствии судить рано.",
        "basis": "Как проводилась оценка",
        "basis_auto": "Автоматическая проверка платформой AccessEdu: оценка {score} из 100, дата {date}.",
        "basis_manual": "Ручной аудит: проверено {done} из {total} пунктов (клавиатура, скринридер, масштабирование и др.).",
        "basis_manual_none": "Ручной аудит пока не проводился.",
        "limits": "Известные ограничения",
        "limits_none": "Известных ограничений не выявлено.",
        "limit_auto": "{title}: {n} элем.",
        "limit_manual": "{title} (ручная проверка)",
        "contact": "Обратная связь",
        "contact_text": "Если вы столкнулись с барьером доступности или нужен материал в другом формате, напишите нам: {contact}. Мы ответим и постараемся устранить проблему в разумный срок.",
        "contact_missing": "[укажите контакт для обратной связи]",
        "org_missing": "Организация",
        "date": "Дата подготовки заявления",
        "note": "Заявление подготовлено на основе данных платформы AccessEdu; перед публикацией проверьте его и при необходимости дополните.",
    },
    "en": {
        "title": "Accessibility statement",
        "intro": "{org} is committed to making “{res}” accessible to everyone, including people with visual, hearing, motor and cognitive disabilities.",
        "standard": "Standard",
        "standard_text": "We aim to follow the Web Content Accessibility Guidelines (WCAG) {ver}, level AA.",
        "status": "Conformance status",
        "status_full": "The resource conforms to WCAG {ver} level AA based on automated testing and a manual audit.",
        "status_partial": "The resource partially conforms to WCAG {ver}.",
        "status_none": "The resource has not been tested yet, so conformance cannot be stated.",
        "basis": "How we assessed it",
        "basis_auto": "Automated testing with AccessEdu: score {score} out of 100, dated {date}.",
        "basis_manual": "Manual audit: {done} of {total} checks completed (keyboard, screen reader, zoom, etc.).",
        "basis_manual_none": "A manual audit has not been performed yet.",
        "limits": "Known limitations",
        "limits_none": "No known limitations.",
        "limit_auto": "{title}: {n} element(s)",
        "limit_manual": "{title} (manual check)",
        "contact": "Feedback",
        "contact_text": "If you run into an accessibility barrier or need content in another format, contact us: {contact}. We will respond and aim to fix the problem within a reasonable time.",
        "contact_missing": "[add a feedback contact]",
        "org_missing": "Our organization",
        "date": "Statement prepared on",
        "note": "This statement was generated from AccessEdu data; review and complete it before publishing.",
    },
}


def build(*, lang: str, resource: dict[str, Any], scan: dict[str, Any] | None, groups: list[dict[str, Any]], audit: dict[str, Any],
          organization: str, contact: str, wcag_version: str) -> dict[str, Any]:
    """Структурированное заявление: заголовок и разделы (список абзацев/пунктов)."""
    t = T.get(lang, T["en"])
    org = organization.strip() or t["org_missing"]
    contact_text = contact.strip() or t["contact_missing"]
    today = date.today().isoformat()

    limits: list[str] = []
    for g in groups:
        if g["manual"] or g["violations"] == 0:
            continue
        limits.append(t["limit_auto"].format(title=g["title"], n=g["violations"]))
    manual_failed = [i["title"] for i in audit["items"] if i["status"] == "fail"]
    limits += [t["limit_manual"].format(title=title) for title in manual_failed]

    progress = audit["progress"]
    if scan is None:
        status = t["status_none"]
    elif scan["level"] == "AA" and not limits and progress["done"] == progress["total"]:
        status = t["status_full"].format(ver=wcag_version)
    else:
        status = t["status_partial"].format(ver=wcag_version)

    basis = []
    if scan is not None:
        basis.append(t["basis_auto"].format(score=round(scan["score"]), date=(scan["created_at"] or "")[:10]))
    basis.append(
        t["basis_manual"].format(done=progress["done"], total=progress["total"]) if progress["done"] else t["basis_manual_none"]
    )
    return {
        "title": t["title"],
        "resource": resource["title"],
        "lang": lang,
        "status_code": "none" if scan is None else ("full" if status == t["status_full"].format(ver=wcag_version) else "partial"),
        "sections": [
            {"heading": None, "paragraphs": [t["intro"].format(org=org, res=resource["title"])]},
            {"heading": t["standard"], "paragraphs": [t["standard_text"].format(ver=wcag_version)]},
            {"heading": t["status"], "paragraphs": [status]},
            {"heading": t["basis"], "items": basis},
            {"heading": t["limits"], "items": limits[:30] or [t["limits_none"]]},
            {"heading": t["contact"], "paragraphs": [t["contact_text"].format(contact=contact_text)]},
        ],
        "footer": f'{t["date"]}: {today}',
        "note": t["note"],
    }


def to_markdown(doc: dict[str, Any]) -> str:
    lines = [f'# {doc["title"]}: {doc["resource"]}', ""]
    for s in doc["sections"]:
        if s["heading"]:
            lines += [f'## {s["heading"]}', ""]
        for p in s.get("paragraphs", []):
            lines += [p, ""]
        for i in s.get("items", []):
            lines.append(f"- {i}")
        if s.get("items"):
            lines.append("")
    lines += [f'_{doc["footer"]}_', "", f'> {doc["note"]}', ""]
    return "\n".join(lines)


def to_html(doc: dict[str, Any]) -> str:
    """Фрагмент для вставки в сайт (разметка семантическая, стили не навязываются)."""
    e = escape
    out = [f'<article lang="{e(doc["lang"])}">', f'<h1>{e(doc["title"])}: {e(doc["resource"])}</h1>']
    for s in doc["sections"]:
        if s["heading"]:
            out.append(f'<h2>{e(s["heading"])}</h2>')
        for p in s.get("paragraphs", []):
            out.append(f"<p>{e(p)}</p>")
        if s.get("items"):
            out.append("<ul>" + "".join(f"<li>{e(i)}</li>" for i in s["items"]) + "</ul>")
    out.append(f'<p><small>{e(doc["footer"])}</small></p>')
    out.append("</article>")
    return "\n".join(out)
