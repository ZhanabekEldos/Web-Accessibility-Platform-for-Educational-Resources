"""Работа с клавиатуры и фокус (WCAG 2.1.1, 2.4.3, 4.1.2)."""
from __future__ import annotations

from bs4 import Tag

from ..document import Document
from ..registry import RuleReport, rule

_MOUSE_HANDLERS = ("onclick", "ondblclick", "onmousedown", "onmouseup")
_NATIVELY_INTERACTIVE = frozenset("a button input select textarea summary option label details".split())
_WIDGET_ROLES = frozenset(
    "button link checkbox radio switch tab menuitem menuitemcheckbox menuitemradio option treeitem slider textbox combobox".split()
)


@rule(
    id="tabindex-positive", wcag=["2.4.3"], level="A", impact="serious", principle="operable", tags=["keyboard"],
    bad='<a href="/a" tabindex="3">Next</a>', good='<a href="/a">Next</a>',
)
def tabindex_positive(doc: Document, report: RuleReport) -> None:
    for el in doc.find_all(tabindex=True):
        index = doc.tabindex(el)
        if index is None:
            continue
        report.checked()
        if index > 0:
            report.fail(el, data={"tabindex": index})


@rule(
    id="mouse-only-handler", wcag=["2.1.1"], level="A", impact="serious", principle="operable", tags=["keyboard", "scripts"],
    bad='<div onclick="openMenu()">Menu</div>',
    good='<button type="button" onclick="openMenu()">Menu</button>',
)
def mouse_only_handler(doc: Document, report: RuleReport) -> None:
    for el in doc.soup.find_all(lambda t: any(t.has_attr(h) for h in _MOUSE_HANDLERS)):
        if el.name in _NATIVELY_INTERACTIVE or not doc.is_exposed(el):
            continue
        report.checked()
        missing = []
        if doc.tabindex(el) is None:
            missing.append("tabindex")
        if (el.get("role") or "").lower() not in _WIDGET_ROLES:
            missing.append("role")
        if missing:
            report.fail(el, data={"missing": missing})


@rule(
    id="focusable-aria-hidden", wcag=["4.1.2"], level="A", impact="serious", principle="robust", tags=["keyboard", "aria"],
    bad='<div aria-hidden="true"><a href="/x">Link</a></div>', good='<div aria-hidden="true"><a href="/x" tabindex="-1">Link</a></div>',
)
def focusable_aria_hidden(doc: Document, report: RuleReport) -> None:
    for el in doc.find_all(attrs={"aria-hidden": lambda v: (v or "").strip().lower() == "true"}):
        parent = el.parent
        if isinstance(parent, Tag) and parent.name != "[document]" and doc.is_aria_hidden(parent):
            continue  # учитываем только внешний скрытый контейнер
        report.checked()
        offenders = [
            n for n in [el, *el.find_all(True)]
            if doc.is_tabbable(n) and not doc.is_disabled(n) and not doc.is_hidden(n)
        ]
        if offenders:
            report.fail(el, data={"focusable": len(offenders), "first": offenders[0].name})
