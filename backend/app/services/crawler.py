"""Поиск страниц сайта для массовой проверки.

Обход ограничен: один сайт (тот же хост), только HTML-страницы, глубина 1–2, не более ``limit`` адресов.
Все загрузки идут через ``fetch_html`` (защита от SSRF сохраняется на каждом шаге).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from ..config import Settings
from .fetcher import FetchError, fetch_html

_SKIP_EXT = re.compile(
    r"\.(pdf|docx?|xlsx?|pptx?|zip|rar|7z|gz|tar|png|jpe?g|gif|svg|webp|ico|bmp|mp3|mp4|avi|mov|webm|wav|ogg|css|js|json|xml|rss|woff2?|ttf|exe|apk|dmg)$",
    re.I,
)
_MAX_DISCOVERY_FETCHES = 6


@dataclass(slots=True)
class FoundPage:
    url: str
    title: str


def normalize(url: str) -> str:
    """Убирает фрагмент и пустой путь, приводит схему и хост к нижнему регистру."""
    url, _ = urldefrag(url)
    p = urlsplit(url)
    path = p.path or "/"
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path, p.query, ""))


def _same_site(a: str, b: str) -> bool:
    pa, pb = urlsplit(a), urlsplit(b)
    host = lambda h: (h or "").lower().removeprefix("www.")  # noqa: E731
    return host(pa.hostname) == host(pb.hostname)


def extract_links(html: str, base_url: str) -> list[FoundPage]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[FoundPage] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
            continue
        absolute = urljoin(base_url, href)
        parts = urlsplit(absolute)
        if parts.scheme not in ("http", "https") or _SKIP_EXT.search(parts.path):
            continue
        text = " ".join(a.get_text(" ", strip=True).split())[:120] or a.get("aria-label", "") or a.get("title", "")
        out.append(FoundPage(normalize(absolute), text))
    return out


def discover(start_url: str, settings: Settings, *, limit: int = 15, depth: int = 1) -> tuple[list[FoundPage], str]:
    """Возвращает (страницы, итоговый адрес стартовой страницы после перенаправлений).

    Стартовая страница всегда первая. Название берётся из ``<title>`` для загруженных страниц, иначе из текста ссылки.
    """
    first = fetch_html(start_url, settings)
    root = normalize(first.url)
    soup_title = _title(first.html)
    found: dict[str, FoundPage] = {root: FoundPage(root, soup_title or urlsplit(root).netloc)}
    queue = [root]
    fetched = {root: first}
    for level in range(depth):
        next_queue: list[str] = []
        for current in queue:
            page = fetched.get(current)
            if page is None:
                continue
            for link in extract_links(page.html, page.url):
                if link.url in found or not _same_site(link.url, root):
                    continue
                found[link.url] = FoundPage(link.url, link.title or urlsplit(link.url).path)
                next_queue.append(link.url)
                if len(found) >= limit:
                    return list(found.values()), root
        if level + 1 >= depth:
            break
        # Для второго уровня загружаем несколько найденных страниц, чтобы взять с них ссылки.
        queue = []
        for url in next_queue[:_MAX_DISCOVERY_FETCHES]:
            try:
                fetched[url] = fetch_html(url, settings)
                found[url].title = _title(fetched[url].html) or found[url].title
                queue.append(url)
            except FetchError:
                continue
    return list(found.values()), root


def _title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return " ".join((soup.title.get_text() if soup.title else "").split())[:200]
