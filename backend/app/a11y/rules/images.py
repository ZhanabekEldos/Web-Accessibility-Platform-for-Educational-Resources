"""Альтернативные тексты для нетекстового содержимого (WCAG 1.1.1)."""
from __future__ import annotations

import re

from ..document import Document
from ..registry import RuleReport, rule

_FILE_EXT = re.compile(r"\.(jpe?g|png|gif|svg|webp|bmp|tiff?|avif)\b", re.I)
_FILENAME_LIKE = re.compile(r"^(img|image|dsc|photo|picture|screenshot|снимок|скриншот)[-_ ]?\d+", re.I)
_GENERIC_ALT = frozenset(
    "image img picture photo graphic icon изображение картинка фото рисунок иконка сурет көрініс".split()
)


@rule(
    id="image-alt", wcag=["1.1.1"], level="A", impact="critical", principle="perceivable", tags=["images"],
    bad='<img src="chart.png">',
    good='<img src="chart.png" alt="Sales grew 20% in 2025">\n<img src="divider.png" alt="">',
)
def image_alt(doc: Document, report: RuleReport) -> None:
    for img in doc.find_all("img"):
        if not doc.is_exposed(img):
            continue
        report.checked()
        if img.has_attr("alt") or img.get("role") in ("presentation", "none"):
            continue
        if doc.accessible_name(img).source in ("aria-label", "aria-labelledby", "title"):
            continue
        report.fail(img)


@rule(
    id="image-alt-quality", wcag=["1.1.1"], level="A", impact="moderate", principle="perceivable", tags=["images"],
    bad='<img src="a.png" alt="IMG_2045.jpg">\n<img src="b.png" alt="image">',
    good='<img src="a.png" alt="Students at a chemistry lab">',
)
def image_alt_quality(doc: Document, report: RuleReport) -> None:
    for img in doc.find_all("img"):
        alt = (img.get("alt") or "").strip()
        if not alt or not doc.is_exposed(img):
            continue
        report.checked()
        low = alt.lower().strip(" .:-_")
        if _FILE_EXT.search(alt) or _FILENAME_LIKE.match(alt) or low in _GENERIC_ALT:
            report.fail(img, data={"alt": alt[:80]})
        elif len(alt) > 150:
            report.review(img, data={"alt_length": len(alt)})


@rule(
    id="image-input-alt", wcag=["1.1.1"], level="A", impact="critical", principle="perceivable", tags=["images", "forms"],
    bad='<input type="image" src="go.png">', good='<input type="image" src="go.png" alt="Search">',
)
def image_input_alt(doc: Document, report: RuleReport) -> None:
    for el in doc.find_all("input", type=lambda t: (t or "").lower() == "image"):
        if not doc.is_exposed(el):
            continue
        report.checked()
        if not doc.accessible_name(el).text:
            report.fail(el)


@rule(
    id="area-alt", wcag=["1.1.1"], level="A", impact="critical", principle="perceivable", tags=["images"],
    bad='<area shape="rect" coords="0,0,50,50" href="/a">', good='<area shape="rect" coords="0,0,50,50" href="/a" alt="Library">',
)
def area_alt(doc: Document, report: RuleReport) -> None:
    for el in doc.find_all("area"):
        if not el.has_attr("href"):
            continue
        report.checked()
        if not doc.accessible_name(el).text:
            report.fail(el)


@rule(
    id="svg-img-alt", wcag=["1.1.1"], level="A", impact="serious", principle="perceivable", tags=["images"],
    bad='<svg role="img" viewBox="0 0 10 10">…</svg>', good='<svg role="img" aria-label="Progress: 70%" viewBox="0 0 10 10">…</svg>',
)
def svg_img_alt(doc: Document, report: RuleReport) -> None:
    for el in doc.find_all("svg"):
        if (el.get("role") or "").lower() not in ("img", "graphics-document") or not doc.is_exposed(el):
            continue
        report.checked()
        if not doc.accessible_name(el).text:
            report.fail(el)


@rule(
    id="embedded-alt", wcag=["1.1.1"], level="A", impact="serious", principle="perceivable", tags=["images", "media"],
    bad='<canvas id="plot"></canvas>', good='<canvas id="plot" aria-label="Temperature plot">Table of values below</canvas>',
)
def embedded_alt(doc: Document, report: RuleReport) -> None:
    for el in doc.find_all("object", "embed", "canvas"):
        if not doc.is_exposed(el):
            continue
        report.checked()
        if doc.accessible_name(el).text:
            continue
        if el.name in ("object", "canvas") and doc.text(el):
            continue  # запасное содержимое внутри элемента
        report.fail(el)
