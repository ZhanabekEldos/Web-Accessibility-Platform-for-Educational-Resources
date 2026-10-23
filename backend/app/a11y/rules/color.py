"""Контрастность текста (WCAG 1.4.3)."""
from __future__ import annotations

import math

from bs4 import NavigableString, Tag

from ..css import blend, contrast_ratio, to_hex
from ..document import NON_RENDERED, Document
from ..registry import RuleReport, rule

_SKIPPED_TAGS = NON_RENDERED | {"option", "optgroup"}


def _has_direct_text(el: Tag) -> bool:
    # ``type(c) is NavigableString`` отсекает комментарии, CDATA и прочие подклассы.
    return any(type(c) is NavigableString and c.strip() for c in el.children)


@rule(
    id="color-contrast", wcag=["1.4.3"], level="AA", impact="serious", principle="perceivable", tags=["color", "visual"],
    bad='<p style="color:#aaa;background:#fff">Hard to read</p>',
    good='<p style="color:#595959;background:#fff">Easy to read</p>',
)
def color_contrast(doc: Document, report: RuleReport) -> None:
    styles = doc.styles
    if not styles.has_color_rules:
        return  # цвета не заданы — браузер использует чёрный на белом, контраст максимальный
    reviewed_backgrounds: set[int] = set()
    for el in doc.soup.find_all(True):
        if el.name in _SKIPPED_TAGS or not _has_direct_text(el):
            continue
        if doc.is_hidden(el) or doc.is_disabled(el):
            continue
        fg = styles.text_color(el)
        if fg is None:
            continue
        bg = styles.background(el)
        if bg.status != "ok":
            node = bg.node
            if node is not None and bg.status == "image" and id(node) not in reviewed_backgrounds:
                reviewed_backgrounds.add(id(node))
                report.checked()
                report.review(el, data={"reason": "background-image"})
            continue
        report.checked()
        fg_rgb = blend(fg, bg.rgb) if fg[3] < 1 else fg[:3]  # type: ignore[arg-type]
        ratio = math.floor(contrast_ratio(fg_rgb, bg.rgb) * 100) / 100  # type: ignore[arg-type]
        large = styles.is_large_text(el)
        required = 3.0 if large else 4.5
        if ratio < required:
            report.fail(
                el,
                data={
                    "ratio": ratio,
                    "required": required,
                    "fg": to_hex(fg_rgb),
                    "bg": to_hex(bg.rgb),  # type: ignore[arg-type]
                    "large": large,
                },
            )
