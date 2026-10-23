"""Формы: подписи полей, группы, автозаполнение, кнопки (WCAG 1.3.1, 1.3.5, 3.3.2, 4.1.2)."""
from __future__ import annotations

import re
from collections import defaultdict

from bs4 import Tag

from ..document import Document
from ..registry import RuleReport, rule

_NON_LABELLED_INPUTS = {"hidden", "submit", "button", "image", "reset"}

# (шаблон по name/id, ожидаемый токен autocomplete)
_PURPOSES: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(p, re.I), token)
    for p, token in (
        (r"e-?mail|почт", "email"),
        (r"(^|[^a-z])(tel|phone|mobile)|телефон", "tel"),
        (r"first.?name|given.?name|fname|^имя$", "given-name"),
        (r"last.?name|family.?name|surname|lname|фамили", "family-name"),
        (r"^(full.?)?name$", "name"),
        (r"user.?name|^login$", "username"),
        (r"new.?pass|confirm.?pass|repeat.?pass", "new-password"),
        (r"pass(word)?$|^pwd$|парол", "current-password"),
        (r"postal|zip|postcode|индекс", "postal-code"),
        (r"b(irth)?day|birth|dob", "bday"),
        (r"street|address|адрес", "street-address"),
        (r"organi[sz]ation|company", "organization"),
    )
)


def _controls(doc: Document) -> list[Tag]:
    result = []
    for el in doc.find_all("input", "select", "textarea"):
        if el.name == "input" and (el.get("type") or "text").lower() in _NON_LABELLED_INPUTS:
            continue
        if doc.is_exposed(el):
            result.append(el)
    return result


@rule(
    id="form-label", wcag=["1.3.1", "4.1.2"], level="A", impact="critical", principle="perceivable", tags=["forms"],
    bad='<input type="text" name="q">',
    good='<label for="q">Search</label>\n<input type="text" id="q" name="q">',
)
def form_label(doc: Document, report: RuleReport) -> None:
    for control in _controls(doc):
        report.checked()
        if doc.accessible_name(control).source is None:
            report.fail(control)


@rule(
    id="placeholder-label", wcag=["3.3.2"], level="A", impact="moderate", principle="understandable", tags=["forms"],
    bad='<input type="email" placeholder="Email">',
    good='<label for="m">Email</label>\n<input type="email" id="m" placeholder="name@example.com">',
)
def placeholder_label(doc: Document, report: RuleReport) -> None:
    for control in _controls(doc):
        if not control.has_attr("placeholder"):
            continue
        report.checked()
        if doc.accessible_name(control).source == "placeholder":
            report.fail(control)


def _expected_autocomplete(el: Tag) -> str | None:
    if el.name != "input":
        return None
    input_type = (el.get("type") or "text").lower()
    if input_type == "email":
        return "email"
    if input_type == "tel":
        return "tel"
    if input_type == "password":
        return "new-password" if re.search(r"new|confirm|repeat", (el.get("name") or "") + (el.get("id") or ""), re.I) else "current-password"
    if input_type not in ("text", "search", "url", "date"):
        return None
    fields = [el.get("name") or "", el.get("id") or ""]
    for pattern, token in _PURPOSES:
        if any(f and pattern.search(f) for f in fields):
            return token
    return None


@rule(
    id="autocomplete", wcag=["1.3.5"], level="AA", impact="moderate", principle="perceivable", tags=["forms"],
    bad='<input type="email" name="email">', good='<input type="email" name="email" autocomplete="email">',
)
def autocomplete(doc: Document, report: RuleReport) -> None:
    for control in _controls(doc):
        expected = _expected_autocomplete(control)
        if expected is None:
            continue
        report.checked()
        value = (control.get("autocomplete") or "").strip().lower()
        if not value or value == "off":
            report.fail(control, data={"expected": expected})


@rule(
    id="radio-group", wcag=["1.3.1"], level="A", impact="moderate", principle="perceivable", tags=["forms"],
    bad='<input type="radio" name="lvl" id="a"><label for="a">Basic</label>\n<input type="radio" name="lvl" id="b"><label for="b">Advanced</label>',
    good='<fieldset><legend>Level</legend>\n  <input type="radio" name="lvl" id="a">…\n</fieldset>',
)
def radio_group(doc: Document, report: RuleReport) -> None:
    groups: dict[tuple[str, str], list[Tag]] = defaultdict(list)
    for el in doc.find_all("input"):
        kind = (el.get("type") or "").lower()
        name = el.get("name")
        if kind in ("radio", "checkbox") and name and doc.is_exposed(el):
            groups[(kind, name)].append(el)
    for (kind, name), members in groups.items():
        if len(members) < 2:
            continue
        report.checked()
        grouped = any(
            m.find_parent("fieldset") is not None
            or m.find_parent(attrs={"role": re.compile(r"^(group|radiogroup)$", re.I)}) is not None
            for m in members
        )
        if not grouped:
            report.fail(members[0], data={"name": name[:40], "count": len(members), "type": kind})


@rule(
    id="button-name", wcag=["4.1.2"], level="A", impact="critical", principle="robust", tags=["forms", "buttons"],
    bad='<button><svg aria-hidden="true">…</svg></button>', good='<button aria-label="Close"><svg aria-hidden="true">…</svg></button>',
)
def button_name(doc: Document, report: RuleReport) -> None:
    candidates = doc.soup.find_all(
        lambda t: t.name == "button"
        or (t.name == "input" and (t.get("type") or "").lower() in ("button", "submit", "reset"))
        or (t.get("role") or "").lower() == "button"
    )
    for el in candidates:
        if not doc.is_exposed(el):
            continue
        report.checked()
        if not doc.accessible_name(el).text:
            report.fail(el)
