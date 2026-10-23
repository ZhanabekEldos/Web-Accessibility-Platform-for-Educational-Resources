"""Ссылки: имя, понятность текста, документы, вложенные интерактивные элементы (WCAG 2.4.4, 4.1.2)."""
from __future__ import annotations

import re

from bs4 import Tag

from ..document import Document
from ..registry import RuleReport, rule

_PUNCT = re.compile(r"[^\w\s]", re.U)
_WS = re.compile(r"\s+")
_GENERIC_LINK_TEXT = frozenset(
    [
        # en
        "click here", "here", "click", "read more", "more", "learn more", "more info", "more information",
        "link", "this link", "details", "continue", "download", "go",
        # ru
        "здесь", "тут", "нажмите здесь", "кликните здесь", "жмите здесь", "подробнее", "читать далее",
        "читать больше", "узнать больше", "далее", "ссылка", "перейти", "скачать", "больше", "еще", "ещё",
        "смотреть", "открыть", "подробности",
        # kk
        "осында", "мұнда", "толығырақ", "толық оқу", "басыңыз", "сілтеме", "жүктеп алу", "көбірек", "әрі қарай",
    ]
)
_DOCUMENT_EXT = re.compile(r"\.(pdf|docx?|pptx?|xlsx?|odt|odp|ods|rtf)(?:$|[?#])", re.I)


def _links(doc: Document) -> list[Tag]:
    found = doc.soup.find_all(lambda t: (t.name == "a" and t.has_attr("href")) or (t.get("role") or "").lower() == "link")
    return [a for a in found if doc.is_exposed(a)]


@rule(
    id="link-name", wcag=["2.4.4", "4.1.2"], level="A", impact="serious", principle="operable", tags=["links"],
    bad='<a href="/course"><img src="logo.png" alt=""></a>', good='<a href="/course"><img src="logo.png" alt="Course home"></a>',
)
def link_name(doc: Document, report: RuleReport) -> None:
    for link in _links(doc):
        report.checked()
        if not doc.accessible_name(link).text:
            report.fail(link)


@rule(
    id="link-text-generic", wcag=["2.4.4"], level="A", impact="moderate", principle="operable", tags=["links", "education"],
    bad='<a href="/syllabus.pdf">click here</a>', good='<a href="/syllabus.pdf">Course syllabus (PDF, 240 KB)</a>',
)
def link_text_generic(doc: Document, report: RuleReport) -> None:
    for link in _links(doc):
        name = doc.accessible_name(link).text
        if not name:
            continue  # такие ссылки ловит link-name
        report.checked()
        normalized = _WS.sub(" ", _PUNCT.sub(" ", name.lower())).strip()
        if normalized in _GENERIC_LINK_TEXT:
            report.fail(link, data={"text": name[:60]})


@rule(
    id="document-link-review", wcag=["2.4.4"], level="BP", impact="moderate", principle="perceivable",
    tags=["links", "education", "documents"], manual=True,
    bad='<a href="/lecture.pdf">Lecture</a>', good='<a href="/lecture.pdf">Lecture (PDF, 1.2 MB, tagged)</a>',
)
def document_link_review(doc: Document, report: RuleReport) -> None:
    for link in _links(doc):
        match = _DOCUMENT_EXT.search(link.get("href") or "")
        if not match:
            continue
        report.checked()
        report.review(link, data={"format": match.group(1).lower()})


_INTERACTIVE_SELECTOR = ("a", "button", "input", "select", "textarea")


@rule(
    id="nested-interactive", wcag=["4.1.2"], level="A", impact="serious", principle="robust", tags=["links", "buttons"],
    bad='<a href="/a"><button>Open</button></a>', good='<a href="/a" class="btn">Open</a>',
)
def nested_interactive(doc: Document, report: RuleReport) -> None:
    containers = doc.soup.find_all(
        lambda t: t.name == "button"
        or (t.name == "a" and t.has_attr("href"))
        or (t.get("role") or "").lower() in ("button", "link")
    )
    for container in containers:
        if not doc.is_exposed(container):
            continue
        report.checked()
        for inner in container.find_all(True):
            if inner.name in _INTERACTIVE_SELECTOR and doc.is_focusable(inner) and doc.is_exposed(inner):
                report.fail(container, data={"inner": inner.name})
                break
