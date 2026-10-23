"""Язык страницы и её частей (WCAG 3.1.1, 3.1.2)."""
from __future__ import annotations

import re

from ..document import Document
from ..registry import RuleReport, rule

_ISO_639_1 = frozenset(
    """aa ab ae af ak am an ar as av ay az ba be bg bh bi bm bn bo br bs ca ce ch co cr cs cu cv cy da de dv dz ee
    el en eo es et eu fa ff fi fj fo fr fy ga gd gl gn gu gv ha he hi ho hr ht hu hy hz ia id ie ig ii ik io is it
    iu ja jv ka kg ki kj kk kl km kn ko kr ks ku kv kw ky la lb lg li ln lo lt lu lv mg mh mi mk ml mn mr ms mt my
    na nb nd ne ng nl nn no nr nv ny oc oj om or os pa pi pl ps pt qu rm rn ro ru rw sa sc sd se sg si sk sl sm sn
    so sq sr ss st su sv sw ta te tg th ti tk tl tn to tr ts tt tw ty ug uk ur uz ve vi vo wa wo xh yi yo za zh zu""".split()
)
_LANG_TAG = re.compile(r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$")

_LATIN_LANGS = frozenset("en de fr es it pt nl pl tr cs sv da fi no nb ro hu id vi".split())
_CYRILLIC_LANGS = frozenset("ru uk be bg kk ky sr mk mn tg tt".split())
_KAZAKH_LETTERS = set("әғқңөұүһӘҒҚҢӨҰҮҺ")


def is_valid_lang(value: str) -> bool:
    value = value.strip()
    if not _LANG_TAG.match(value):
        return value.lower().startswith("x-")
    primary = value.split("-")[0].lower()
    return primary in _ISO_639_1 or len(primary) == 3


@rule(
    id="html-lang", wcag=["3.1.1"], level="A", impact="serious", principle="understandable", tags=["document", "language"],
    bad="<html>", good='<html lang="ru">',
)
def html_lang(doc: Document, report: RuleReport) -> None:
    if not doc.is_full_document:
        return
    report.checked()
    if not doc.lang:
        report.fail(doc.html_tag)


@rule(
    id="html-lang-valid", wcag=["3.1.1"], level="A", impact="serious", principle="understandable", tags=["document", "language"],
    bad='<html lang="russian">', good='<html lang="ru">',
)
def html_lang_valid(doc: Document, report: RuleReport) -> None:
    if not doc.is_full_document or not doc.lang:
        return
    report.checked()
    if not is_valid_lang(doc.lang):
        report.fail(doc.html_tag, data={"lang": doc.lang[:20]})


@rule(
    id="lang-parts-valid", wcag=["3.1.2"], level="AA", impact="moderate", principle="understandable", tags=["language"],
    bad='<blockquote lang="english">…</blockquote>', good='<blockquote lang="en">…</blockquote>',
)
def lang_parts_valid(doc: Document, report: RuleReport) -> None:
    for el in doc.find_all(lang=True):
        if el.name == "html":
            continue
        value = el.get("lang")
        if not isinstance(value, str) or not value.strip():
            continue  # пустой lang допустим — «язык неизвестен»
        report.checked()
        if not is_valid_lang(value):
            report.fail(el, data={"lang": value[:20]})


def _script_stats(text: str) -> tuple[int, int, int]:
    cyrillic = latin = kazakh = 0
    for ch in text:
        if "а" <= ch.lower() <= "я" or ch in "ёЁіІїЇєЄ" or ch in _KAZAKH_LETTERS:
            cyrillic += 1
            if ch in _KAZAKH_LETTERS:
                kazakh += 1
        elif "a" <= ch.lower() <= "z":
            latin += 1
    return cyrillic, latin, kazakh


@rule(
    id="lang-content-mismatch", wcag=["3.1.1"], level="A", impact="moderate", principle="understandable",
    tags=["document", "language", "education"],
    bad='<html lang="en"><body><p>Добро пожаловать на курс…</p></body></html>',
    good='<html lang="ru"><body><p>Добро пожаловать на курс…</p></body></html>',
)
def lang_content_mismatch(doc: Document, report: RuleReport) -> None:
    """Эвристика: язык, заявленный в ``lang``, сверяется с алфавитом основного текста."""
    if not doc.is_full_document or not doc.lang or not is_valid_lang(doc.lang):
        return
    root = doc.soup.find("body") or doc.soup
    text = doc.text(root)[:30_000]
    cyrillic, latin, kazakh = _script_stats(text)
    letters = cyrillic + latin
    if letters < 100:
        return
    report.checked()
    declared = doc.lang.split("-")[0].lower()
    cyr_share = cyrillic / letters
    detected: str | None = None
    if declared in _LATIN_LANGS and cyr_share > 0.6:
        detected = "ru" if kazakh / max(cyrillic, 1) < 0.02 else "kk"
    elif declared in _CYRILLIC_LANGS and cyr_share < 0.2:
        detected = "latin"
    elif declared == "ru" and cyrillic >= 100 and kazakh / cyrillic >= 0.02:
        detected = "kk"
    elif declared == "kk" and cyrillic >= 200 and kazakh / cyrillic < 0.005:
        detected = "ru"
    if detected:
        report.review(doc.html_tag, data={"declared": declared, "detected": detected})
