import http.server
import threading
import unittest

from app.config import Settings
from app.services.fetcher import FetchError, fetch_html, is_public_ip, validate_url


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/ok":
            body = "<html lang='ru'><title>Привет</title><body><h1>Мир</h1></body></html>".encode("cp1251")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=windows-1251")
        elif self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/ok")
            body = b""
        elif self.path == "/loop":
            self.send_response(302)
            self.send_header("Location", "/loop")
            body = b""
        elif self.path == "/json":
            body = b"{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        elif self.path == "/big":
            body = b"x" * 5000
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
        else:
            body = b"nope"
            self.send_response(404)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class IpTests(unittest.TestCase):
    def test_private_ranges_blocked(self):
        for ip in ("127.0.0.1", "10.1.2.3", "192.168.0.5", "172.16.0.1", "169.254.169.254", "0.0.0.0", "::1", "fe80::1", "::ffff:127.0.0.1", "100.64.0.1", "224.0.0.1"):
            self.assertFalse(is_public_ip(ip), ip)
        for ip in ("8.8.8.8", "1.1.1.1", "2606:4700:4700::1111"):
            self.assertTrue(is_public_ip(ip), ip)

    def test_url_validation(self):
        for bad in ("", "ftp://example.com", "javascript:alert(1)", "http://", "https://user:pw@example.com", "file:///etc/passwd"):
            with self.assertRaises(FetchError, msg=bad):
                validate_url(bad)

    def test_localhost_blocked_by_default(self):
        for url in ("http://localhost/", "http://127.0.0.1:8000/", "http://[::1]/", "http://0.0.0.0/", "http://169.254.169.254/latest/meta-data/"):
            with self.assertRaises(FetchError, msg=url) as ctx:
                validate_url(url)
            self.assertEqual(ctx.exception.code, "blocked_host")

    def test_fetch_refuses_internal_address(self):
        with self.assertRaises(FetchError) as ctx:
            fetch_html("http://127.0.0.1:9/", Settings())
        self.assertEqual(ctx.exception.code, "blocked_host")


class LocalServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.settings = Settings(allow_private_hosts=True, max_html_bytes=1000, fetch_timeout=5)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_fetch_and_decode_cp1251(self):
        page = fetch_html(self.base + "/ok", self.settings)
        self.assertIn("Привет", page.html)

    def test_follows_redirect(self):
        self.assertTrue(fetch_html(self.base + "/redirect", self.settings).url.endswith("/ok"))

    def test_redirect_loop(self):
        with self.assertRaises(FetchError) as ctx:
            fetch_html(self.base + "/loop", self.settings)
        self.assertEqual(ctx.exception.code, "too_many_redirects")

    def test_non_html_rejected(self):
        with self.assertRaises(FetchError) as ctx:
            fetch_html(self.base + "/json", self.settings)
        self.assertEqual(ctx.exception.code, "not_html")

    def test_size_limit(self):
        with self.assertRaises(FetchError) as ctx:
            fetch_html(self.base + "/big", self.settings)
        self.assertEqual(ctx.exception.code, "too_large")

    def test_http_error(self):
        with self.assertRaises(FetchError) as ctx:
            fetch_html(self.base + "/missing", self.settings)
        self.assertEqual(ctx.exception.code, "http_error")

    def test_connection_guard_blocks_even_if_validation_skipped(self):
        """Защита на уровне соединения (против DNS-rebinding): внутренний IP недоступен, даже если проверка URL пройдена."""
        from urllib3.util import connection

        from app.services import fetcher

        host, port = self.server.server_address
        fetcher._guard.active, fetcher._guard.allow_private = True, False
        try:
            with self.assertRaises(FetchError) as ctx:
                connection.create_connection((host, port), timeout=2)
            self.assertEqual(ctx.exception.code, "blocked_host")
        finally:
            fetcher._guard.active = False
        # вне запроса загрузчика соединения работают как обычно
        connection.create_connection((host, port), timeout=2).close()


if __name__ == "__main__":
    unittest.main()
