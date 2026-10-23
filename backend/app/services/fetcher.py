"""Загрузка HTML по URL с защитой от SSRF.

* допускаются только http/https;
* адрес проверяется не только до запроса, но и в момент соединения
  (защита от DNS-rebinding) и после каждого перенаправления;
* ограничены размер ответа, время и число перенаправлений.
"""
from __future__ import annotations

import ipaddress
import socket
import threading
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import requests
from urllib3.util import connection as _u3_connection

from ..config import Settings


class FetchError(Exception):
    """Ошибка загрузки. ``code`` — машинный код, ``message`` — для пользователя."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(slots=True)
class FetchedPage:
    url: str
    html: str
    status: int


_guard = threading.local()
_original_create_connection = _u3_connection.create_connection


def is_public_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return addr.is_global and not addr.is_multicast


def _guarded_create_connection(address, *args, **kwargs):
    """Подменяет ``urllib3.util.connection.create_connection``: проверяет IP непосредственно перед соединением."""
    if not getattr(_guard, "active", False) or getattr(_guard, "allow_private", False):
        return _original_create_connection(address, *args, **kwargs)
    host, port = address
    host = host.strip("[]")
    last_error: Exception | None = None
    for family, socktype, proto, _, sockaddr in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
        if not is_public_ip(sockaddr[0]):
            last_error = FetchError("blocked_host", "Адрес указывает во внутреннюю сеть — проверка запрещена настройками")
            continue
        # Соединяемся с уже проверенным IP — повторного DNS-запроса нет.
        try:
            return _original_create_connection((sockaddr[0], port), *args, **kwargs)
        except OSError as exc:
            last_error = exc
    raise last_error or OSError("Не удалось соединиться")


_u3_connection.create_connection = _guarded_create_connection


def validate_url(url: str, *, allow_private: bool = False) -> str:
    url = (url or "").strip()
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise FetchError("invalid_url", "Нужен адрес вида https://example.com/page")
    if parts.username or parts.password:
        raise FetchError("invalid_url", "Адреса с логином и паролем не поддерживаются")
    if not allow_private:
        try:
            infos = socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80), 0, socket.SOCK_STREAM)
        except socket.gaierror:
            raise FetchError("dns_error", "Не удалось найти сайт по этому адресу") from None
        if not infos or any(not is_public_ip(i[4][0]) for i in infos):
            raise FetchError("blocked_host", "Адрес указывает во внутреннюю сеть — проверка запрещена настройками")
    return url


def fetch_html(url: str, settings: Settings) -> FetchedPage:
    session = requests.Session()
    session.trust_env = False  # прокси из окружения нарушили бы проверку адреса
    session.headers.update({"User-Agent": settings.user_agent, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5", "Accept-Language": "ru,en;q=0.8"})
    _guard.active = True
    _guard.allow_private = settings.allow_private_hosts
    try:
        current = validate_url(url, allow_private=settings.allow_private_hosts)
        for _ in range(settings.max_redirects + 1):
            try:
                resp = session.get(current, timeout=settings.fetch_timeout, allow_redirects=False, stream=True)
            except requests.exceptions.SSLError:
                raise FetchError("ssl_error", "Ошибка сертификата безопасности сайта") from None
            except requests.exceptions.Timeout:
                raise FetchError("timeout", "Сайт не ответил вовремя") from None
            except FetchError:
                raise
            except requests.exceptions.ConnectionError as exc:
                cause = exc.args[0] if exc.args else None
                inner = getattr(cause, "reason", None) or cause
                if isinstance(inner, FetchError):
                    raise inner from None
                raise FetchError("connection_error", "Не удалось соединиться с сайтом") from None
            except requests.exceptions.RequestException:
                raise FetchError("request_error", "Не удалось загрузить страницу") from None
            try:
                if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("Location")
                    if not location:
                        raise FetchError("bad_redirect", "Сайт вернул некорректное перенаправление")
                    current = validate_url(urljoin(current, location), allow_private=settings.allow_private_hosts)
                    continue
                if resp.status_code >= 400:
                    raise FetchError("http_error", f"Сайт ответил ошибкой {resp.status_code}")
                ctype = (resp.headers.get("Content-Type") or "").lower()
                if ctype and not any(t in ctype for t in ("html", "xml", "text/plain")):
                    raise FetchError("not_html", "По адресу находится не HTML-страница")
                declared = resp.headers.get("Content-Length")
                if declared and declared.isdigit() and int(declared) > settings.max_html_bytes:
                    raise FetchError("too_large", "Страница слишком большая для проверки")
                body = bytearray()
                for chunk in resp.iter_content(65536):
                    body += chunk
                    if len(body) > settings.max_html_bytes:
                        raise FetchError("too_large", "Страница слишком большая для проверки")
                encoding = resp.encoding if "charset" in ctype else None
                text = _decode(bytes(body), encoding)
                return FetchedPage(url=current, html=text, status=resp.status_code)
            finally:
                resp.close()
        raise FetchError("too_many_redirects", "Слишком много перенаправлений")
    finally:
        _guard.active = False
        session.close()


def _decode(body: bytes, encoding: str | None) -> str:
    candidates = [encoding] if encoding else []
    head = body[:2048].lower()
    marker = b"charset="
    if marker in head:
        tail = head.split(marker, 1)[1].lstrip(b"\"' ")
        name = bytes(c for c in tail[:20] if chr(c).isalnum() or chr(c) in "-_").decode("ascii", "ignore")
        if name:
            candidates.append(name)
    candidates += ["utf-8", "cp1251"]
    for enc in candidates:
        try:
            return body.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="replace")
