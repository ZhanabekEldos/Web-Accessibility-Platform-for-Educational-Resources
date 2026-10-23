import unittest

from .helpers import ApiTestCase


class Basics(ApiTestCase):
    def test_health_meta_rules(self):
        self.assertEqual(self.client.get("/api/health").json["status"], "ok")
        meta = self.client.get("/api/meta").json
        self.assertIn("ru", meta["languages"])
        rules = self.client.get("/api/rules?lang=ru").json
        self.assertEqual(rules["total"], meta["rules_total"])
        first = rules["items"][0]
        self.assertTrue(first["title"] and first["wcag"] is not None)

    def test_unknown_route_is_json(self):
        resp = self.client.get("/api/nope")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json["error"]["code"], "not_found")

    def test_invalid_json(self):
        resp = self.client.post("/api/collections", data="not json", content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json["error"]["code"], "invalid_json")

    def test_security_headers(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.headers["X-Content-Type-Options"], "nosniff")


class Collections(ApiTestCase):
    def test_crud_and_duplicates(self):
        created = self.client.post("/api/collections", json={"name": "Химия", "description": "d"})
        self.assertEqual(created.status_code, 201)
        cid = created.json["id"]
        self.assertEqual(self.client.post("/api/collections", json={"name": "Химия"}).status_code, 409)
        self.assertEqual(self.client.post("/api/collections", json={"name": ""}).status_code, 422)
        self.assertEqual(self.client.patch(f"/api/collections/{cid}", json={"name": "Химия 2"}).json["name"], "Химия 2")
        self.assertEqual(self.client.patch("/api/collections/999", json={"name": "x"}).status_code, 404)
        self.assertEqual(self.client.delete(f"/api/collections/{cid}").status_code, 204)
        self.assertEqual(self.client.delete(f"/api/collections/{cid}").status_code, 404)

    def test_unknown_fields_rejected(self):
        self.assertEqual(self.client.post("/api/collections", json={"name": "x", "evil": 1}).status_code, 422)


class Resources(ApiTestCase):
    def test_validation(self):
        self.assertEqual(self.client.post("/api/resources", json={"title": "x"}).status_code, 422)
        self.assertEqual(self.client.post("/api/resources", json={"title": "x", "url": "ftp://a"}).status_code, 422)
        self.assertEqual(self.client.post("/api/resources", json={"title": "x", "html": "<p>", "collection_id": 99}).status_code, 422)

    def test_create_scan_and_list(self):
        resp = self.client.post("/api/resources?scan=1", json={"title": "Страница", "html": "<html lang='ru'><head><title>T</title></head><body><main><h1>x</h1><img src='a.png'></main></body></html>"})
        self.assertEqual(resp.status_code, 201)
        self.assertLess(resp.json["resource"]["last_score"], 100)
        self.assertEqual(resp.json["scan"]["groups"][0]["rule_id"], "image-alt")
        listing = self.client.get("/api/resources?q=Стран").json
        self.assertEqual(listing["total"], 1)
        self.assertEqual(self.client.get("/api/resources?q=zzz").json["total"], 0)
        self.assertEqual(self.client.get("/api/resources?band=unscanned").json["total"], 0)

    def test_search_escapes_like_wildcards(self):
        self.make_resource(title="100% доступность")
        self.make_resource(title="Другое")
        self.assertEqual(self.client.get("/api/resources?q=%25").json["total"], 1)
        self.assertEqual(self.client.get("/api/resources?q=_").json["total"], 0)

    def test_sort_puts_unscanned_last(self):
        a = self.make_resource(title="A")
        self.make_resource(title="B")
        self.client.post(f"/api/resources/{a['id']}/scan")
        items = self.client.get("/api/resources?sort=score&order=asc").json["items"]
        self.assertEqual([i["title"] for i in items], ["A", "B"])

    def test_patch_and_delete(self):
        r = self.make_resource()
        self.assertEqual(self.client.patch(f"/api/resources/{r['id']}", json={"title": "Новое"}).json["title"], "Новое")
        self.assertEqual(self.client.delete(f"/api/resources/{r['id']}").status_code, 204)
        self.assertEqual(self.client.get(f"/api/resources/{r['id']}").status_code, 404)

    def test_scan_history_diff_and_triage(self):
        r = self.make_resource()
        first = self.client.post(f"/api/resources/{r['id']}/scan").json
        finding = first["findings"][0]
        t = self.client.put(f"/api/resources/{r['id']}/triage/{finding['fingerprint']}", json={"status": "wontfix", "note": "декор"})
        self.assertEqual(t.json["status"], "wontfix")
        self.client.patch(f"/api/resources/{r['id']}", json={"html": "<html lang='ru'><head><title>T</title></head><body><main><h1>x</h1><img src='a.png' alt='Схема'></main></body></html>"})
        second = self.client.post(f"/api/resources/{r['id']}/scan").json
        self.assertGreater(second["score"], first["score"])
        self.assertEqual(second["previous"]["id"], first["id"])
        diff = self.client.get(f"/api/scans/{second['id']}/diff").json
        self.assertEqual(diff["counts"]["fixed"], 1)
        self.assertGreater(diff["score_delta"], 0)
        self.assertEqual(len(self.client.get(f"/api/resources/{r['id']}/scans").json["items"]), 2)
        self.assertEqual(self.client.put(f"/api/resources/{r['id']}/triage/unknown", json={"status": "fixed"}).status_code, 404)
        self.assertEqual(self.client.put(f"/api/resources/{r['id']}/triage/{finding['fingerprint']}", json={"status": "bogus"}).status_code, 422)

    def test_deleting_scan_restores_previous_state(self):
        r = self.make_resource()
        a = self.client.post(f"/api/resources/{r['id']}/scan").json
        b = self.client.post(f"/api/resources/{r['id']}/scan").json
        self.client.delete(f"/api/scans/{b['id']}")
        self.assertEqual(self.client.get(f"/api/resources/{r['id']}").json["last_scan_id"], a["id"])
        self.client.delete(f"/api/scans/{a['id']}")
        self.assertIsNone(self.client.get(f"/api/resources/{r['id']}").json["last_score"])


class Scans(ApiTestCase):
    def test_adhoc_html_scan_is_not_stored_as_resource(self):
        resp = self.client.post("/api/scans", json={"html": "<img src='a.png'>"})
        self.assertEqual(resp.status_code, 201)
        self.assertIsNone(resp.json["resource_id"])
        self.assertEqual(self.client.get("/api/resources").json["total"], 0)

    def test_save_as_creates_resource(self):
        resp = self.client.post("/api/scans", json={"html": "<img src='a.png'>", "save_as": {"title": "Сохранённая"}})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(self.client.get("/api/resources").json["total"], 1)

    def test_exactly_one_source(self):
        self.assertEqual(self.client.post("/api/scans", json={}).status_code, 422)
        self.assertEqual(self.client.post("/api/scans", json={"html": "<p>", "url": "http://x.y"}).status_code, 422)

    def test_blocked_url_returns_clear_error(self):
        resp = self.client.post("/api/scans", json={"url": "http://127.0.0.1:1/"})
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json["error"]["code"], "blocked_host")

    def test_failed_scan_is_recorded_for_resource(self):
        r = self.make_resource(html=None, url="http://169.254.169.254/")
        resp = self.client.post(f"/api/resources/{r['id']}/scan")
        self.assertEqual(resp.status_code, 422)
        history = self.client.get(f"/api/resources/{r['id']}/scans").json["items"]
        self.assertEqual(history[0]["status"], "error")
        self.assertIsNone(self.client.get(f"/api/resources/{r['id']}").json["last_score"])

    def test_language_switch(self):
        scan_id = self.client.post("/api/scans", json={"html": "<img src='a.png'>"}).json["id"]
        ru = self.client.get(f"/api/scans/{scan_id}?lang=ru").json["findings"][0]["message"]
        en = self.client.get(f"/api/scans/{scan_id}?lang=en").json["findings"][0]["message"]
        self.assertNotEqual(ru, en)

    def test_exports(self):
        r = self.make_resource()
        scan = self.client.post(f"/api/resources/{r['id']}/scan").json
        for fmt, marker in (("json", '"score"'), ("csv", "image-alt"), ("html", "<!doctype html>")):
            resp = self.client.get(f"/api/scans/{scan['id']}/export?format={fmt}&lang=ru")
            self.assertEqual(resp.status_code, 200, fmt)
            self.assertIn(marker, resp.get_data(as_text=True))
            self.assertIn("attachment", resp.headers["Content-Disposition"])
        self.assertEqual(self.client.get(f"/api/scans/{scan['id']}/export?format=exe").status_code, 400)

    def test_html_export_escapes_content(self):
        payload = "<html lang='ru'><head><title>T</title></head><body><main><h1>x</h1><img src='\"><script>alert(1)</script>'></main></body></html>"
        scan = self.client.post("/api/scans", json={"html": payload}).json
        out = self.client.get(f"/api/scans/{scan['id']}/export?format=html").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", out)

    def test_csv_export_neutralises_formulas(self):
        from app.services.reports import _csv_safe

        self.assertEqual(_csv_safe("=HYPERLINK(1)"), "'=HYPERLINK(1)")
        self.assertEqual(_csv_safe("обычный"), "обычный")

    def test_batch(self):
        a, b = self.make_resource(title="A"), self.make_resource(title="B")
        resp = self.client.post("/api/scans/batch", json={"resource_ids": [a["id"], b["id"], 999]}).json
        self.assertEqual((resp["ok"], resp["failed"]), (2, 1))
        coll = self.client.post("/api/collections", json={"name": "К"}).json["id"]
        self.client.patch(f"/api/resources/{a['id']}", json={"collection_id": coll})
        self.assertEqual(self.client.post("/api/scans/batch", json={"collection_id": coll}).json["ok"], 1)
        self.assertEqual(self.client.post("/api/scans/batch", json={}).status_code, 422)


class Stats(ApiTestCase):
    def test_empty_overview(self):
        data = self.client.get("/api/stats/overview").json
        self.assertEqual(data["totals"]["resources"], 0)
        self.assertIsNone(data["totals"]["avg_score"])

    def test_demo_seed_is_idempotent_and_populates_everything(self):
        self.assertEqual(self.client.post("/api/demo/seed").status_code, 201)
        self.assertEqual(self.client.post("/api/demo/seed").status_code, 200)
        data = self.client.get("/api/stats/overview").json
        self.assertEqual(data["totals"]["resources"], 3)
        self.assertEqual(data["totals"]["scanned"], 3)
        self.assertGreater(data["improvement"]["avg_delta"], 0)
        self.assertTrue(data["trend"] and data["top_rules"] and data["worst"])
        coll = self.client.get("/api/collections").json["items"][0]
        self.assertEqual(coll["resources_count"], 3)
        scoped = self.client.get(f"/api/stats/overview?collection_id={coll['id']}").json
        self.assertEqual(scoped["totals"]["resources"], 3)


class StaticServing(ApiTestCase):
    def test_spa_fallback_when_dist_exists(self):
        import os

        from app.config import Settings
        from app.factory import create_app

        dist = os.path.join(self.tmp, "dist")
        os.makedirs(os.path.join(dist, "assets"))
        for name, text in (("index.html", "<!doctype html><title>app</title>"), ("assets/a.js", "1")):
            with open(os.path.join(dist, name), "w") as fh:
                fh.write(text)
        client = create_app(Settings(db_path=self.settings.db_path, static_dir=dist)).test_client()
        with client.get("/resources/12") as page:
            self.assertIn("app", page.get_data(as_text=True))
        with client.get("/assets/a.js") as asset:
            self.assertEqual(asset.status_code, 200)
            self.assertIn("immutable", asset.headers["Cache-Control"])
        self.assertEqual(client.get("/api/missing").status_code, 404)


if __name__ == "__main__":
    unittest.main()
