"""Структура страницы: заголовок, заголовки разделов, ориентиры, списки, таблицы (WCAG 1.3.1, 2.4.x, 2.2.x)."""
from __future__ import annotations

import re

from bs4 import Tag

from ..document import Document
from ..registry import RuleReport, rule

_GENERIC_TITLES = frozenset(
    "untitled document untitled-document new-page index home page без-названия без названия документ страница тақырыпсыз".split()
)
_HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")


def _heading_level(el: Tag) -> int | None:
    if re.fullmatch(r"h[1-6]", el.name):
        return int(el.name[1])
    if (el.get("role") or "").lower() == "heading":
        try:
            return int(el.get("aria-level", ""))
        except ValueError:
            return None
    return None


def _headings(doc: Document) -> list[Tag]:
    elements = doc.soup.find_all(lambda t: t.name in _HEADING_TAGS or (t.get("role") or "").lower() == "heading")
    return [el for el in elements if doc.is_exposed(el)]


@rule(
    id="document-title", wcag=["2.4.2"], level="A", impact="serious", principle="operable", tags=["document"],
    bad="<head></head>", good="<head><title>Limits — Calculus, lecture 3</title></head>",
)
def document_title(doc: Document, report: RuleReport) -> None:
    if not doc.is_full_document:
        return
    report.checked()
    title_el = doc.soup.find("title")
    text = doc.title
    anchor = title_el or doc.soup.find("head") or doc.html_tag
    if not text:
        report.fail(anchor, data={"reason": "missing"})
    elif text.lower() in _GENERIC_TITLES:
        report.fail(anchor, data={"reason": "generic", "title": text[:80]})


@rule(
    id="page-has-h1", wcag=["2.4.6"], level="BP", impact="moderate", principle="operable", tags=["document", "headings"],
    bad="<h2>Welcome</h2>", good="<h1>Course: Introduction to Chemistry</h1>",
)
def page_has_h1(doc: Document, report: RuleReport) -> None:
    if not doc.is_full_document:
        return
    report.checked()
    if not any(_heading_level(h) == 1 and doc.text(h) for h in _headings(doc)):
        report.fail(doc.soup.find("body") or doc.html_tag)


@rule(
    id="heading-order", wcag=["1.3.1"], level="BP", impact="moderate", principle="perceivable", tags=["headings"],
    bad="<h1>Course</h1>\n<h4>Week 1</h4>", good="<h1>Course</h1>\n<h2>Week 1</h2>",
)
def heading_order(doc: Document, report: RuleReport) -> None:
    previous: int | None = None
    for heading in _headings(doc):
        level = _heading_level(heading)
        if level is None:
            continue
        if previous is not None:
            report.checked()
            if level > previous + 1:
                report.fail(heading, data={"from": previous, "to": level})
        previous = level


@rule(
    id="heading-empty", wcag=["2.4.6"], level="AA", impact="serious", principle="operable", tags=["headings"],
    bad="<h2></h2>", good="<h2>Assignments</h2>",
)
def heading_empty(doc: Document, report: RuleReport) -> None:
    for heading in _headings(doc):
        report.checked()
        if not doc.accessible_name(heading).text:
            report.fail(heading)


@rule(
    id="landmark-main", wcag=["1.3.1"], level="BP", impact="moderate", principle="perceivable", tags=["document", "landmarks"],
    bad="<body><div>…</div></body>", good="<body><main>…</main></body>",
)
def landmark_main(doc: Document, report: RuleReport) -> None:
    if not doc.is_full_document:
        return
    report.checked()
    mains = [m for m in doc.soup.find_all(lambda t: t.name == "main" or (t.get("role") or "").lower() == "main") if doc.is_exposed(m)]
    if not mains:
        report.fail(doc.soup.find("body") or doc.html_tag, data={"count": 0})
    elif len(mains) > 1:
        report.fail(mains[1], data={"count": len(mains)})


@rule(
    id="bypass-blocks", wcag=["2.4.1"], level="A", impact="moderate", principle="operable", tags=["document", "keyboard"],
    bad="<body><nav>…100 links…</nav><div>Content</div></body>",
    good='<body><a href="#content" class="skip">Skip to content</a>\n<nav>…</nav><main id="content">…</main></body>',
)
def bypass_blocks(doc: Document, report: RuleReport) -> None:
    if not doc.is_full_document:
        return
    report.checked()
    if doc.soup.find(lambda t: t.name == "main" or (t.get("role") or "").lower() == "main") or _headings(doc):
        return
    tabbable = [a for a in doc.find_all("a", "button", "input", "select", "textarea") if doc.is_tabbable(a)][:10]
    for el in tabbable:
        href = el.get("href") or ""
        if el.name == "a" and href.startswith("#") and len(href) > 1 and doc.by_id(href[1:]):
            return
    report.fail(doc.soup.find("body") or doc.html_tag)


@rule(
    id="list-structure", wcag=["1.3.1"], level="A", impact="serious", principle="perceivable", tags=["lists"],
    bad="<div><li>One</li><li>Two</li></div>", good="<ul><li>One</li><li>Two</li></ul>",
)
def list_structure(doc: Document, report: RuleReport) -> None:
    for li in doc.find_all("li"):
        report.checked()
        parent = li.parent
        ok = isinstance(parent, Tag) and (parent.name in ("ul", "ol", "menu") or (parent.get("role") or "").lower() == "list")
        if not ok:
            report.fail(li)
    for lst in doc.find_all("ul", "ol"):
        report.checked()
        bad_children = [
            c for c in lst.children if isinstance(c, Tag) and c.name not in ("li", "script", "template", "style")
        ]
        if bad_children:
            report.fail(lst, data={"child": bad_children[0].name})


@rule(
    id="table-headers", wcag=["1.3.1"], level="A", impact="serious", principle="perceivable", tags=["tables"],
    bad="<table><tr><td>Name</td><td>Grade</td></tr><tr><td>Ann</td><td>5</td></tr></table>",
    good="<table><tr><th scope=\"col\">Name</th><th scope=\"col\">Grade</th></tr>…</table>",
)
def table_headers(doc: Document, report: RuleReport) -> None:
    for table in doc.find_all("table"):
        if (table.get("role") or "").lower() in ("presentation", "none") or not doc.is_exposed(table):
            continue
        rows = table.find_all("tr")
        if len(rows) < 2 or max((len(r.find_all(["td", "th"], recursive=False)) for r in rows), default=0) < 2:
            continue  # похоже на таблицу-раскладку
        report.checked()
        has_header = table.find("th") or table.find(attrs={"role": re.compile(r"^(row|column)header$", re.I)})
        if not has_header:
            report.fail(table)


@rule(
    id="duplicate-id", wcag=["4.1.2"], level="BP", impact="moderate", principle="robust", tags=["document"],
    bad='<div id="menu"></div><div id="menu"></div>', good='<div id="menu"></div><div id="menu-footer"></div>',
)
def duplicate_id(doc: Document, report: RuleReport) -> None:
    seen: set[str] = set()
    for el in doc.soup.find_all(id=True):
        value = el.get("id")
        if not isinstance(value, str) or not value.strip():
            continue
        report.checked()
        if value in seen:
            report.fail(el, data={"id": value[:60]})
        seen.add(value)


@rule(
    id="meta-refresh", wcag=["2.2.1"], level="A", impact="critical", principle="operable", tags=["document"],
    bad='<meta http-equiv="refresh" content="30">', good="<!-- обновление страницы по запросу пользователя -->",
)
def meta_refresh(doc: Document, report: RuleReport) -> None:
    for meta in doc.find_all("meta", **{"http-equiv": lambda v: (v or "").lower() == "refresh"}):
        report.checked()
        match = re.match(r"\s*(\d+)", meta.get("content") or "")
        delay = int(match.group(1)) if match else 0
        if 0 < delay < 72000:
            report.fail(meta, data={"delay": delay})


@rule(
    id="blink-marquee", wcag=["2.2.2"], level="A", impact="serious", principle="operable", tags=["motion"],
    bad="<marquee>News</marquee>", good="<p>News</p>",
)
def blink_marquee(doc: Document, report: RuleReport) -> None:
    for el in doc.find_all("blink", "marquee"):
        report.checked()
        report.fail(el)


@rule(
    id="viewport-zoom", wcag=["1.4.4"], level="AA", impact="critical", principle="perceivable", tags=["document", "mobile"],
    bad='<meta name="viewport" content="width=device-width, user-scalable=no">',
    good='<meta name="viewport" content="width=device-width, initial-scale=1">',
)
def viewport_zoom(doc: Document, report: RuleReport) -> None:
    for meta in doc.find_all("meta", attrs={"name": lambda v: (v or "").lower() == "viewport"}):
        report.checked()
        content = (meta.get("content") or "").lower()
        params = dict(
            (k.strip(), v.strip()) for k, _, v in (p.partition("=") for p in content.split(",") if "=" in p)
        )
        scalable = params.get("user-scalable", "")
        try:
            max_scale = float(params["maximum-scale"]) if "maximum-scale" in params else None
        except ValueError:
            max_scale = None
        if scalable in ("no", "0") or (max_scale is not None and max_scale < 2):
            report.fail(meta, data={"user_scalable": scalable or None, "maximum_scale": max_scale})


@rule(
    id="frame-title", wcag=["4.1.2", "2.4.1"], level="A", impact="serious", principle="robust", tags=["document", "media"],
    bad='<iframe src="map.html"></iframe>', good='<iframe src="map.html" title="Campus map"></iframe>',
)
def frame_title(doc: Document, report: RuleReport) -> None:
    for frame in doc.find_all("iframe", "frame"):
        if not doc.is_exposed(frame):
            continue
        report.checked()
        if not doc.accessible_name(frame).text:
            report.fail(frame)
