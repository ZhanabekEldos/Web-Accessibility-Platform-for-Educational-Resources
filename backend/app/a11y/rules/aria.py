"""Корректность WAI-ARIA (WCAG 4.1.2)."""
from __future__ import annotations

from ..aria_data import IDREF_ATTRS, REQUIRED_ATTRS, VALID_ARIA_ATTRS, is_valid_role
from ..document import Document
from ..registry import RuleReport, rule


@rule(
    id="aria-valid-role", wcag=["4.1.2"], level="A", impact="critical", principle="robust", tags=["aria"],
    bad='<div role="buton">Send</div>', good='<div role="button" tabindex="0">Send</div>',
)
def aria_valid_role(doc: Document, report: RuleReport) -> None:
    for el in doc.find_all(role=True):
        tokens = (el.get("role") or "").lower().split()
        if not tokens:
            continue
        report.checked()
        if not any(is_valid_role(t) for t in tokens):
            report.fail(el, data={"role": " ".join(tokens)[:40]})


@rule(
    id="aria-valid-attr", wcag=["4.1.2"], level="A", impact="critical", principle="robust", tags=["aria"],
    bad='<button aria-lable="Close">×</button>', good='<button aria-label="Close">×</button>',
)
def aria_valid_attr(doc: Document, report: RuleReport) -> None:
    for el in doc.soup.find_all(lambda t: any(a.startswith("aria-") for a in t.attrs)):
        report.checked()
        unknown = [a for a in el.attrs if a.startswith("aria-") and a.lower() not in VALID_ARIA_ATTRS]
        if unknown:
            report.fail(el, data={"attrs": unknown[:5]})


@rule(
    id="aria-idref", wcag=["4.1.2"], level="A", impact="critical", principle="robust", tags=["aria"],
    bad='<input aria-labelledby="missing-id">', good='<span id="lbl">Name</span>\n<input aria-labelledby="lbl">',
)
def aria_idref(doc: Document, report: RuleReport) -> None:
    for el in doc.soup.find_all(lambda t: any(t.has_attr(a) for a in IDREF_ATTRS)):
        for attr in IDREF_ATTRS:
            raw = el.get(attr)
            if not isinstance(raw, str) or not raw.strip():
                continue
            if attr in ("aria-controls", "aria-owns") and (el.get("aria-expanded") or "").lower() == "false":
                continue  # управляемый элемент может отсутствовать в свёрнутом состоянии
            report.checked()
            refs = raw.split()
            missing = [r for r in refs if doc.by_id(r) is None]
            broken = len(missing) == len(refs) if attr in ("aria-labelledby", "aria-describedby") else bool(missing)
            if broken:
                report.fail(el, data={"attr": attr, "missing": missing[:5]})


@rule(
    id="aria-required-attr", wcag=["4.1.2"], level="A", impact="critical", principle="robust", tags=["aria"],
    bad='<div role="checkbox" tabindex="0">Agree</div>', good='<div role="checkbox" tabindex="0" aria-checked="false">Agree</div>',
)
def aria_required_attr(doc: Document, report: RuleReport) -> None:
    for el in doc.find_all(role=True):
        role = (el.get("role") or "").lower().split()[:1]
        if not role or role[0] not in REQUIRED_ATTRS:
            continue
        role_name = role[0]
        # Нативные элементы сами предоставляют состояние / уровень.
        if el.name == "input" and (el.get("type") or "").lower() in ("checkbox", "radio", "range"):
            continue
        if role_name == "heading" and el.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            continue
        report.checked()
        missing = [a for a in REQUIRED_ATTRS[role_name] if not el.has_attr(a)]
        if missing:
            report.fail(el, data={"role": role_name, "missing": missing})
