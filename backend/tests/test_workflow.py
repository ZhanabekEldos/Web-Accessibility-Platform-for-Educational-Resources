import http.server
import threading
import unittest

from app.a11y import checklist
from app.data import academy
from app.repositories import resources as resources_repo
from app.services.crawler import extract_links, normalize
from app.services.scheduler import run_due

from .helpers import ApiTestCase

GOOD = "<html lang='ru'><head><title>T</title></head><body><main><h1>Привет</h1><img src='a.png' alt='кот'></main></body></html>"
BAD = "<html lang='ru'><head><title>T</title></head><body><main><h1>Привет</h1><img src='a.png'><img src='b.png'></main></body></html>"
IMG_FIX = "<html lang='ru'><head><title>T</title></head><body><main><h1>Привет</h1><img src='a.png' alt='кот'><img src='b.png' alt='пёс'></main></body></html>"


class Audit(ApiTestCase):
    def test_catalog_is_consistent(self):
        ids = [i.id for i in checklist.ITEMS]
        self.assertEqual(len(ids), len(set(ids)))
        for item in checklist.ITEMS:
            self.assertTrue(item.ru[0] and item.ru[1] and item.en[0] and item.en[1], item.id)
            self.assertTrue(item.wcag, item.id)  # критерии существуют (иначе KeyError в catalog)
        checklist.catalog("ru")

    def test_set_and_progress(self):
        rid = self.make_resource()["id"]
        a = self.client.get(f"/api/resources/{rid}/audit").json
        self.assertEqual(a["progress"]["done"], 0)
        self.assertEqual(a["progress"]["total"], len(checklist.ITEMS))
        r = self.client.put(f"/api/resources/{rid}/audit/captions", json={"status": "fail", "note": "нет субтитров"})
        self.assertEqual(r.status_code, 200)
        self.client.put(f"/api/resources/{rid}/audit/zoom", json={"status": "pass"})
        a = self.client.get(f"/api/resources/{rid}/audit").json
        self.assertEqual((a["progress"]["done"], a["progress"]["fail"], a["progress"]["pass"]), (2, 1, 1))
        item = next(i for i in a["items"] if i["id"] == "captions")
        self.assertEqual((item["status"], item["note"]), ("fail", "нет субтитров"))
        # сброс
        a = self.client.put(f"/api/resources/{rid}/audit/captions", json={"status": None}).json
        self.assertEqual(a["progress"]["done"], 1)

    def test_validation(self):
        rid = self.make_resource()["id"]
        self.assertEqual(self.client.put(f"/api/resources/{rid}/audit/nope", json={"status": "pass"}).status_code, 404)
        self.assertEqual(self.client.put(f"/api/resources/{rid}/audit/zoom", json={"status": "maybe"}).status_code, 422)
        self.assertEqual(self.client.put("/api/resources/999/audit/zoom", json={"status": "pass"}).status_code, 404)

    def test_audit_deleted_with_resource(self):
        rid = self.make_resource()["id"]
        self.client.put(f"/api/resources/{rid}/audit/zoom", json={"status": "pass"})
        self.client.delete(f"/api/resources/{rid}")
        row = self.raw_db().execute("SELECT COUNT(*) FROM audit_items").fetchone()[0]
        self.assertEqual(row, 0)


class Statement(ApiTestCase):
    def test_statement_partial_then_html_escaped(self):
        res = self.make_resource(title="Курс <b>Химия</b>", html=BAD)
        self.client.post(f"/api/resources/{res['id']}/scan")
        st = self.client.get(f"/api/resources/{res['id']}/statement?organization=Школа&contact=a@b.kz").json
        self.assertEqual(st["status_code"], "partial")
        text = " ".join(" ".join(s.get("paragraphs", []) + s.get("items", [])) for s in st["sections"])
        self.assertIn("a@b.kz", text)
        html = self.client.get(f"/api/resources/{res['id']}/statement?format=html").get_data(as_text=True)
        self.assertNotIn("<b>Химия</b>", html)
        self.assertIn("&lt;b&gt;", html)
        md = self.client.get(f"/api/resources/{res['id']}/statement?format=md")
        self.assertIn("text/markdown", md.content_type)

    def test_unscanned_and_bad_format(self):
        rid = self.make_resource()["id"]
        self.assertEqual(self.client.get(f"/api/resources/{rid}/statement").json["status_code"], "none")
        self.assertEqual(self.client.get(f"/api/resources/{rid}/statement?format=exe").status_code, 400)

    def test_manual_failures_listed_as_limitations(self):
        res = self.make_resource(html=GOOD)
        self.client.post(f"/api/resources/{res['id']}/scan")
        self.client.put(f"/api/resources/{res['id']}/audit/captions", json={"status": "fail"})
        st = self.client.get(f"/api/resources/{res['id']}/statement?lang=en").json
        limits = next(s for s in st["sections"] if s["heading"] == "Known limitations")["items"]
        self.assertTrue(any("manual check" in i for i in limits))
        self.assertEqual(st["status_code"], "partial")


class Badge(ApiTestCase):
    def test_badge_svg(self):
        res = self.make_resource(html=GOOD)
        r = self.client.get(f"/api/resources/{res['id']}/badge.svg")
        self.assertEqual(r.mimetype, "image/svg+xml")
        self.assertIn('role="img"', r.get_data(as_text=True))
        self.client.post(f"/api/resources/{res['id']}/scan")
        svg = self.client.get(f"/api/resources/{res['id']}/badge.svg").get_data(as_text=True)
        self.assertIn("100", svg)
        self.assertEqual(self.client.get("/api/resources/999/badge.svg").status_code, 404)


class Events(ApiTestCase):
    def _rescan_with(self, rid, html):
        self.client.patch(f"/api/resources/{rid}", json={"html": html})
        return self.client.post(f"/api/resources/{rid}/scan").json

    def test_first_scan_silent_then_drop_and_rise(self):
        rid = self.make_resource(html=GOOD)["id"]
        self.client.post(f"/api/resources/{rid}/scan")
        self.assertEqual(self.client.get("/api/events").json["total"], 0)
        self._rescan_with(rid, BAD)
        types = {e["type"] for e in self.client.get("/api/events").json["items"]}
        self.assertIn("score_drop", types)
        self.assertIn("new_critical", types)
        self._rescan_with(rid, IMG_FIX)
        types = {e["type"] for e in self.client.get("/api/events").json["items"]}
        self.assertIn("score_rise", types)

    def test_read_flow(self):
        rid = self.make_resource(html=GOOD)["id"]
        self.client.post(f"/api/resources/{rid}/scan")
        self._rescan_with(rid, BAD)
        unread = self.client.get("/api/events/unread-count").json["unread"]
        self.assertGreater(unread, 0)
        first = self.client.get("/api/events").json["items"][0]
        self.assertEqual(first["resource_title"], "Тест")
        r = self.client.post("/api/events/read", json={"ids": [first["id"]]}).json
        self.assertEqual(r["unread"], unread - 1)
        self.assertEqual(self.client.post("/api/events/read", json={}).json["unread"], 0)
        self.assertEqual(self.client.get("/api/events?unread=1").json["total"], 0)
        self.assertEqual(self.client.delete("/api/events").status_code, 204)
        self.assertEqual(self.client.get("/api/events").json["total"], 0)

    def test_adhoc_scans_do_not_notify(self):
        self.client.post("/api/scans", json={"html": GOOD})
        self.client.post("/api/scans", json={"html": BAD})
        self.assertEqual(self.client.get("/api/events").json["total"], 0)

    def test_failed_scan_notifies(self):
        rid = self.client.post("/api/resources", json={"title": "x", "url": "http://127.0.0.1:9/nope"}).json["resource"]["id"]
        self.assertEqual(self.client.post(f"/api/resources/{rid}/scan").status_code, 422)
        self.assertEqual(self.client.get("/api/events").json["items"][0]["type"], "scan_failed")


class Schedule(ApiTestCase):
    def test_schedule_set_and_run_due(self):
        rid = self.make_resource(schedule="daily")["id"]
        res = self.client.get(f"/api/resources/{rid}").json
        self.assertEqual(res["schedule"], "daily")
        self.assertIsNotNone(res["next_run_at"])
        # срок ещё не наступил
        self.assertEqual(run_due(self.settings), 0)
        conn = self.raw_db()
        conn.execute("UPDATE resources SET next_run_at = '2000-01-01T00:00:00.000Z' WHERE id = ?", (rid,))
        conn.commit()
        self.assertEqual(run_due(self.settings), 1)
        after = self.client.get(f"/api/resources/{rid}").json
        self.assertIsNotNone(after["last_scan_id"])
        self.assertGreater(after["next_run_at"], "2020")
        self.assertEqual(run_due(self.settings), 0)  # сдвинуто вперёд, повторно не запускается

    def test_off_clears_and_invalid_rejected(self):
        rid = self.make_resource(schedule="weekly")["id"]
        res = self.client.patch(f"/api/resources/{rid}", json={"schedule": "off"}).json
        self.assertIsNone(res["next_run_at"])
        self.assertEqual(self.client.patch(f"/api/resources/{rid}", json={"schedule": "hourly"}).status_code, 422)

    def test_claim_is_exclusive(self):
        rid = self.make_resource(schedule="daily")["id"]
        conn = self.raw_db()
        conn.execute("UPDATE resources SET next_run_at = '2000-01-01T00:00:00.000Z' WHERE id = ?", (rid,))
        conn.commit()
        self.assertEqual(resources_repo.claim_due(conn), [rid])
        self.assertEqual(resources_repo.claim_due(conn), [])


class Academy(ApiTestCase):
    def test_content_consistent(self):
        ids = set()
        for lesson in academy.LESSONS:
            self.assertNotIn(lesson["id"], ids)
            ids.add(lesson["id"])
            ru, en = lesson["ru"], lesson["en"]
            self.assertEqual(len(ru["sections"]), len(en["sections"]), lesson["id"])
            self.assertEqual(bool(ru["example"]), bool(en["example"]))
            self.assertGreaterEqual(len(lesson["quiz"]), 3)
            for q in lesson["quiz"]:
                self.assertEqual(len(q["ru"]["options"]), len(q["en"]["options"]))
                self.assertTrue(0 <= q["answer"] < len(q["ru"]["options"]))

    def test_listing_hides_answers(self):
        items = self.client.get("/api/academy").json["items"]
        self.assertEqual(len(items), len(academy.LESSONS))
        lesson = self.client.get(f"/api/academy/{items[0]['id']}").json
        self.assertNotIn("answer", str(lesson["quiz"]))
        self.assertIsNone(lesson["prev"])

    def test_quiz_flow_and_progress(self):
        lid = academy.LESSONS[0]["id"]
        n = len(academy.LESSONS[0]["quiz"])
        wrong = [(q["answer"] + 1) % len(q["ru"]["options"]) for q in academy.LESSONS[0]["quiz"]]
        r = self.client.post(f"/api/academy/{lid}/quiz", json={"answers": wrong}).json
        self.assertEqual((r["score"], r["passed"]), (0, False))
        self.assertTrue(all(not x["correct"] for x in r["results"]))
        self.assertEqual(self.client.get("/api/academy").json["completed"], 0)
        right = [q["answer"] for q in academy.LESSONS[0]["quiz"]]
        r = self.client.post(f"/api/academy/{lid}/quiz", json={"answers": right}).json
        self.assertEqual((r["score"], r["total"], r["passed"]), (n, n, True))
        listing = self.client.get("/api/academy").json
        self.assertEqual(listing["completed"], 1)
        self.assertEqual(listing["items"][0]["progress"]["attempts"], 2)
        # провал после успеха не отменяет прохождение
        self.client.post(f"/api/academy/{lid}/quiz", json={"answers": wrong})
        self.assertEqual(self.client.get("/api/academy").json["completed"], 1)

    def test_quiz_validation(self):
        lid = academy.LESSONS[0]["id"]
        self.assertEqual(self.client.post(f"/api/academy/{lid}/quiz", json={"answers": [0]}).status_code, 422)
        self.assertEqual(self.client.post(f"/api/academy/{lid}/quiz", json={"answers": [99, 99, 99]}).status_code, 422)
        self.assertEqual(self.client.post("/api/academy/nope/quiz", json={"answers": []}).status_code, 404)
        self.assertEqual(self.client.get("/api/academy/nope").status_code, 404)


class SiteHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        pages = {
            "/": "<html lang='ru'><title>Главная</title><body><main><h1>Главная</h1><a href='/a'>Тема А</a> <a href='/b#x'>Тема Б</a>"
                 "<a href='/doc.pdf'>PDF</a><a href='mailto:x@y.z'>почта</a><a href='http://other.example/z'>Чужой</a><a href='/a'>дубль</a></main></body></html>",
            "/a": "<html lang='ru'><title>Тема А</title><body><main><h1>А</h1><img src='x.png'><a href='/c'>Глубже</a></main></body></html>",
            "/b": "<html lang='ru'><title>Тема Б</title><body><main><h1>Б</h1></main></body></html>",
            "/c": "<html lang='ru'><title>Глубокая</title><body><main><h1>В</h1></main></body></html>",
        }
        body = pages.get(self.path.split("?")[0])
        if body is None:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class Crawl(ApiTestCase):
    settings_overrides = {"allow_private_hosts": True}

    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), SiteHandler)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_extract_links_filters(self):
        links = extract_links("<a href='/x#f'>X</a><a href='#'>y</a><a href='/f.zip'>z</a><a href='javascript:1'>j</a><a href='/p?q=1'>P</a>", "http://h.example/dir/")
        self.assertEqual([l.url for l in links], ["http://h.example/x", "http://h.example/p?q=1"])
        self.assertEqual(normalize("HTTP://Ex.com#a"), "http://ex.com/")

    def test_discover_depth1_same_site_only(self):
        r = self.client.post("/api/crawl/discover", json={"url": self.base + "/"}).json
        urls = [p["url"] for p in r["pages"]]
        self.assertEqual(urls[0], self.base + "/")
        self.assertEqual(set(urls), {self.base + "/", self.base + "/a", self.base + "/b"})
        self.assertEqual(r["pages"][0]["title"], "Главная")

    def test_discover_depth2_and_limit(self):
        deep = [p["url"] for p in self.client.post("/api/crawl/discover", json={"url": self.base + "/", "depth": 2}).json["pages"]]
        self.assertIn(self.base + "/c", deep)
        short = self.client.post("/api/crawl/discover", json={"url": self.base + "/", "limit": 2}).json["pages"]
        self.assertEqual(len(short), 2)

    def test_discover_errors(self):
        self.assertEqual(self.client.post("/api/crawl/discover", json={"url": "ftp://x"}).status_code, 422)
        self.assertEqual(self.client.post("/api/crawl/discover", json={"url": ""}).status_code, 422)
        self.assertEqual(self.client.post("/api/crawl/discover", json={"url": self.base + "/missing"}).status_code, 502)

    def test_import_creates_collection_scans_and_skips_duplicates(self):
        pages = [{"url": self.base + "/a", "title": "Тема А"}, {"url": self.base + "/b", "title": "Тема Б"}]
        r = self.client.post("/api/crawl/import", json={"pages": pages, "collection_name": "Сайт курса"}).json
        self.assertEqual((r["created"], r["skipped"], r["ok"], r["failed"]), (2, 0, 2, 0))
        cols = self.client.get("/api/collections").json["items"]
        self.assertEqual(cols[0]["resources_count"], 2)
        again = self.client.post("/api/crawl/import", json={"pages": pages, "collection_id": r["collection_id"], "scan": False}).json
        self.assertEqual((again["created"], again["skipped"]), (0, 2))
        res = self.client.get("/api/resources?per_page=50").json["items"]
        a = next(x for x in res if x["title"] == "Тема А")
        self.assertLess(a["last_score"], 100)  # на странице А есть картинка без alt

    def test_import_validation(self):
        self.assertEqual(self.client.post("/api/crawl/import", json={"pages": []}).status_code, 422)
        self.assertEqual(self.client.post("/api/crawl/import", json={"pages": [{"url": "ftp://x"}]}).status_code, 422)
        self.assertEqual(self.client.post("/api/crawl/import", json={"pages": [{"url": self.base + "/a"}], "collection_id": 999}).status_code, 404)


class CrawlBlocked(ApiTestCase):
    def test_internal_hosts_blocked(self):
        r = self.client.post("/api/crawl/discover", json={"url": "http://127.0.0.1:8000/"})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json["error"]["code"], "blocked_host")
        r = self.client.post("/api/crawl/import", json={"pages": [{"url": "http://169.254.169.254/"}]})
        self.assertEqual(r.status_code, 422)


class CollectionReport(ApiTestCase):
    def test_report_formats(self):
        cid = self.client.post("/api/collections", json={"name": "Химия"}).json["id"]
        a = self.make_resource(title="=cmd|' /C calc'!A0", html=BAD, collection_id=cid)
        self.make_resource(title="B", html=GOOD, collection_id=cid)
        self.client.post(f"/api/resources/{a['id']}/scan")
        csv_text = self.client.get(f"/api/collections/{cid}/report?format=csv").get_data(as_text=True)
        self.assertIn("'=cmd", csv_text)
        html = self.client.get(f"/api/collections/{cid}/report").get_data(as_text=True)
        self.assertIn("Химия", html)
        self.assertIn("<th scope=\"col\">", html)
        self.assertEqual(self.client.get(f"/api/collections/{cid}/report?format=pdf").status_code, 400)
        self.assertEqual(self.client.get("/api/collections/999/report").status_code, 404)


if __name__ == "__main__":
    unittest.main()
