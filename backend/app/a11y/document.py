"""Обёртка над разобранным HTML с общими помощниками для правил.

Правила работают не с «сырым» BeautifulSoup, а с ``Document``: здесь живут
вычисление доступного имени, скрытость элементов, CSS-путь и фрагмент кода
для отчёта, а также кэши, чтобы десятки правил не повторяли одну и ту же работу.
"""
from __future__ import annotations

import re
from functools import cached_property
from typing import NamedTuple

from bs4 import BeautifulSoup, Comment, Declaration, Doctype, NavigableString, ProcessingInstruction, Tag

from .css import StyleEngine

_WS = re.compile(r"\s+")

VOID_TAGS = frozenset("area base br col embed hr img input link meta param source track wbr".split())
NON_RENDERED = frozenset("script style template noscript head title meta link".split())
BLOCK_TAGS = frozenset(
    """address article aside blockquote body br dd details dialog div dl dt fieldset figcaption figure footer form
    h1 h2 h3 h4 h5 h6 header hr li main nav ol p pre section summary table td th tr ul""".split()
)
# Блочные контейнеры, внутреннее содержимое которых в отчёте обрезается.
_COMPACT_SNIPPET = frozenset(
    "html body table ul ol dl form main section article div header footer nav aside select tbody thead tr fieldset".split()
)
_NON_TEXT_NODES = (Comment, Doctype, Declaration, ProcessingInstruction)

_FOCUSABLE_INPUT_EXCLUDED = {"hidden"}


class AccName(NamedTuple):
    text: str
    source: str | None  # aria-labelledby | aria-label | label | alt | content | value | title | placeholder | None


class Document:
    def __init__(self, html: str) -> None:
        self.html = html
        self.soup = BeautifulSoup(html, "html.parser")
        self.is_full_document = self.soup.find("html") is not None
        self._hidden: dict[int, bool] = {}
        self._aria_hidden: dict[int, bool] = {}
        self._selectors: dict[int, str] = {}

    # ------------------------------------------------------------------ поиск
    def find_all(self, *names: str, **attrs) -> list[Tag]:
        return self.soup.find_all(list(names) or True, **attrs)

    def select(self, css: str) -> list[Tag]:
        return self.soup.select(css)

    @cached_property
    def styles(self) -> StyleEngine:
        return StyleEngine(self.soup)

    @cached_property
    def ids(self) -> dict[str, Tag]:
        """Первый элемент для каждого значения ``id``."""
        result: dict[str, Tag] = {}
        for el in self.soup.find_all(id=True):
            value = el.get("id")
            if isinstance(value, str) and value and value not in result:
                result[value] = el
        return result

    def by_id(self, value: str) -> Tag | None:
        return self.ids.get(value)

    @cached_property
    def html_tag(self) -> Tag | None:
        return self.soup.find("html")

    @cached_property
    def title(self) -> str:
        el = self.soup.find("title")
        return _WS.sub(" ", el.get_text()).strip() if el else ""

    @cached_property
    def lang(self) -> str | None:
        el = self.html_tag
        value = el.get("lang") or el.get("xml:lang") if el else None
        return value.strip() if isinstance(value, str) else None

    # ------------------------------------------------------------------ видимость
    def _self_hidden(self, el: Tag) -> bool:
        if el.name in NON_RENDERED:
            return True
        if el.has_attr("hidden") and el.get("hidden") != "until-found":
            return True
        if el.name == "dialog" and not el.has_attr("open"):
            return True  # стили браузера по умолчанию: закрытый диалог не отображается
        if el.name == "input" and (el.get("type") or "").lower() in _FOCUSABLE_INPUT_EXCLUDED:
            return True
        return self.styles.is_display_none(el)

    def is_hidden(self, el: Tag) -> bool:
        """Элемент не отображается (``hidden``, ``display:none``, служебный тег) — сам или через предка."""
        key = id(el)
        cached = self._hidden.get(key)
        if cached is not None:
            return cached
        node: Tag | None = el
        result = False
        while isinstance(node, Tag) and node.name != "[document]":
            if self._self_hidden(node):
                result = True
                break
            node = node.parent
        self._hidden[key] = result
        return result

    def is_aria_hidden(self, el: Tag) -> bool:
        key = id(el)
        cached = self._aria_hidden.get(key)
        if cached is not None:
            return cached
        node: Tag | None = el
        result = False
        while isinstance(node, Tag) and node.name != "[document]":
            if (node.get("aria-hidden") or "").strip().lower() == "true":
                result = True
                break
            node = node.parent
        self._aria_hidden[key] = result
        return result

    def is_exposed(self, el: Tag) -> bool:
        """Элемент доступен вспомогательным технологиям."""
        return not self.is_hidden(el) and not self.is_aria_hidden(el)

    # ------------------------------------------------------------------ текст и имена
    def text(self, el: Tag) -> str:
        """Видимый текст элемента; ``alt`` изображений и ``aria-label`` вложенных элементов учитываются."""
        parts: list[str] = []
        self._collect_text(el, parts)
        return _WS.sub(" ", "".join(parts)).strip()

    def _collect_text(self, node: Tag, parts: list[str]) -> None:
        for child in node.children:
            if isinstance(child, _NON_TEXT_NODES):
                continue
            if isinstance(child, NavigableString):
                parts.append(str(child))
                continue
            if not isinstance(child, Tag) or self._self_hidden(child):
                continue
            if (child.get("aria-hidden") or "").strip().lower() == "true":
                continue
            if child.name == "img":
                alt = child.get("alt")
                if alt:
                    parts.append(f" {alt} ")
                continue
            if child.name == "svg":
                title = child.find("title")
                label = child.get("aria-label") or (title.get_text() if title else "")
                if label:
                    parts.append(f" {label} ")
                continue
            label = (child.get("aria-label") or "").strip()
            if label:
                parts.append(f" {label} ")
                continue
            block = child.name in BLOCK_TAGS
            if block:
                parts.append(" ")
            self._collect_text(child, parts)
            if block:
                parts.append(" ")

    def _labelledby_text(self, el: Tag) -> str:
        names: list[str] = []
        for ref in (el.get("aria-labelledby") or "").split():
            target = self.by_id(ref)
            if target is None:
                continue
            label = (target.get("aria-label") or "").strip()
            names.append(label or self._text_including_hidden(target))
        return _WS.sub(" ", " ".join(n for n in names if n)).strip()

    def _text_including_hidden(self, target: Tag) -> str:
        # Элемент, на который ссылается aria-labelledby, учитывается даже скрытым.
        return _WS.sub(" ", target.get_text(" ")).strip()

    def labels_for(self, el: Tag) -> list[Tag]:
        """``<label>``, связанные с полем формы (через ``for`` или вложенностью)."""
        labels: list[Tag] = []
        el_id = el.get("id")
        if el_id:
            labels.extend(l for l in self.soup.find_all("label", attrs={"for": el_id}))
        parent_label = el.find_parent("label")
        if parent_label is not None and all(l is not parent_label for l in labels):
            labels.append(parent_label)
        return labels

    def accessible_name(self, el: Tag) -> AccName:
        """Упрощённое вычисление доступного имени (accname) для типовых элементов."""
        text = self._labelledby_text(el)
        if text:
            return AccName(text, "aria-labelledby")
        label = (el.get("aria-label") or "").strip()
        if label:
            return AccName(label, "aria-label")

        name = el.name
        input_type = (el.get("type") or "text").lower() if name == "input" else ""

        if name in ("img", "area") or input_type == "image":
            alt = (el.get("alt") or "").strip()
            if alt:
                return AccName(alt, "alt")
        elif name == "input" and input_type in ("button", "submit", "reset"):
            value = (el.get("value") or "").strip()
            if value or input_type in ("submit", "reset"):
                return AccName(value or input_type, "value")
        elif name in ("input", "select", "textarea", "meter", "progress", "output"):
            for lab in self.labels_for(el):
                lab_text = self.text(lab)
                if lab_text:
                    return AccName(lab_text, "label")
        elif name == "svg":
            title = el.find("title")
            if title and title.get_text().strip():
                return AccName(_WS.sub(" ", title.get_text()).strip(), "content")
        elif name in ("a", "button", "summary", "label", "legend", "caption", "th", "option") or el.get("role") in (
            "button", "link", "tab", "menuitem", "option", "heading",
        ) or re.fullmatch(r"h[1-6]", name):
            content = self.text(el)
            if content:
                return AccName(content, "content")
        elif name in ("iframe", "frame", "object", "embed", "canvas"):
            pass  # имя берётся из title / aria-*

        title_attr = (el.get("title") or "").strip()
        if title_attr:
            return AccName(title_attr, "title")
        if name in ("input", "textarea"):
            placeholder = (el.get("placeholder") or "").strip()
            if placeholder:
                return AccName(placeholder, "placeholder")
        return AccName("", None)

    # ------------------------------------------------------------------ фокус
    def is_disabled(self, el: Tag) -> bool:
        if el.has_attr("disabled"):
            return True
        return (el.get("aria-disabled") or "").lower() == "true"

    def tabindex(self, el: Tag) -> int | None:
        raw = el.get("tabindex")
        if raw is None:
            return None
        try:
            return int(str(raw).strip())
        except ValueError:
            return None

    def is_focusable(self, el: Tag) -> bool:
        """Может ли элемент получить фокус (в том числе программно)."""
        if self.tabindex(el) is not None:
            return True
        name = el.name
        if name in ("a", "area"):
            return el.has_attr("href")
        if name in ("button", "select", "textarea"):
            return not el.has_attr("disabled")
        if name == "input":
            return (el.get("type") or "text").lower() != "hidden" and not el.has_attr("disabled")
        if name in ("audio", "video"):
            return el.has_attr("controls")
        if name in ("iframe", "summary"):
            return True
        return (el.get("contenteditable") or "").lower() in ("", "true") and el.has_attr("contenteditable")

    def is_tabbable(self, el: Tag) -> bool:
        index = self.tabindex(el)
        return self.is_focusable(el) and (index is None or index >= 0)

    # ------------------------------------------------------------------ для отчётов
    def selector(self, el: Tag) -> str:
        """Уникальный CSS-путь к элементу (обрывается на ближайшем элементе с уникальным id)."""
        key = id(el)
        cached = self._selectors.get(key)
        if cached is not None:
            return cached
        segments: list[str] = []
        node: Tag | None = el
        while isinstance(node, Tag) and node.name != "[document]":
            el_id = node.get("id")
            if isinstance(el_id, str) and el_id and self.ids.get(el_id) is node and re.fullmatch(r"[A-Za-z][\w-]*", el_id):
                segments.append(f"{node.name}#{el_id}")
                break
            if node.name in ("html", "body", "head"):
                segments.append(node.name)
            else:
                same = node.parent.find_all(node.name, recursive=False) if node.parent else [node]
                if len(same) > 1:
                    # Сравнение по идентичности: Tag.__eq__ сравнивает содержимое, а не позицию.
                    position = next((i for i, s in enumerate(same, 1) if s is node), 1)
                    segments.append(f"{node.name}:nth-of-type({position})")
                else:
                    segments.append(node.name)
            node = node.parent
        segments.reverse()
        if len(segments) > 6:
            segments = ["…"] + segments[-6:]
        result = " > ".join(segments)
        self._selectors[key] = result
        return result

    _IDENTITY_ATTRS = ("id", "name", "src", "href", "for", "type", "role", "data-src")

    def identity(self, el: Tag) -> str:
        """Устойчивая «личность» элемента для отпечатка замечания (не зависит от позиции и стилей)."""
        parts = [el.name]
        for attr in self._IDENTITY_ATTRS:
            value = el.get(attr)
            if isinstance(value, str) and value:
                parts.append(f"{attr}={value[:80]}")
        if el.name not in _COMPACT_SNIPPET:
            parts.append(self.text(el)[:40])
        return "|".join(parts)

    def open_tag(self, el: Tag) -> str:
        attrs = []
        for name, value in el.attrs.items():
            if isinstance(value, list):
                value = " ".join(value)
            value = str(value)
            if len(value) > 80:
                value = value[:77] + "…"
            attrs.append(name if value == "" else f'{name}="{value.replace(chr(34), "&quot;")}"')
        return "<" + " ".join([el.name, *attrs]) + ">"

    def snippet(self, el: Tag, limit: int = 220) -> str:
        """Короткий фрагмент HTML для отчёта."""
        opening = self.open_tag(el)
        if el.name in VOID_TAGS or not el.contents:
            return opening if el.name in VOID_TAGS else f"{opening}</{el.name}>"
        closing = f"</{el.name}>"
        if el.name not in _COMPACT_SNIPPET:
            raw = _WS.sub(" ", str(el)).strip()
            if len(raw) <= limit:
                return raw
        budget = max(20, limit - len(opening) - len(closing))
        inner = self.text(el)
        if len(inner) > budget:
            inner = inner[: budget - 1].rstrip() + "…"
        return f"{opening}{inner}{closing}" if inner else f"{opening}…{closing}"
