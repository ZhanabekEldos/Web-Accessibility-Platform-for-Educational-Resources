import unittest

from app.a11y import tools
from app.a11y.css import contrast_ratio, parse_color

from .helpers import ApiTestCase

RU_EASY = "Мама мыла раму. Папа читал газету. Мы пошли гулять в парк. Там было тепло и тихо. Дети играли в мяч. Собака бегала по траве. Потом все пили чай дома. Вечером мы смотрели кино. Это был хороший день для всех нас."
RU_HARD = ("Осуществление комплексного мониторирования функционирования образовательно-информационной инфраструктуры предполагает "
           "предварительную стандартизацию методологических принципов, обуславливающих целесообразность дифференцированного "
           "администрирования соответствующих подсистем в условиях ограниченности ресурсов, а также необходимость институционализации "
           "ответственности руководителей структурных подразделений за своевременность предоставления отчётности.")


class Contrast(unittest.TestCase):
    def test_known_ratios(self):
        r = tools.contrast_report("#000", "#fff")
        self.assertEqual(r["ratio"], 21.0)
        self.assertTrue(all(r["checks"].values()))
        grey = tools.contrast_report("#999", "#fff")
        self.assertEqual(grey["ratio"], 2.84)  # 2.8485… — округление вниз
        self.assertFalse(grey["checks"]["aa_normal"])
        self.assertFalse(grey["checks"]["aa_large"])

    def test_never_rounds_up(self):
        # #777 на белом — 4.48 : 1: не проходит 4.5 и не должен округляться до него
        r = tools.contrast_report("#777777", "#ffffff")
        self.assertLess(r["ratio"], 4.5)
        self.assertFalse(r["checks"]["aa_normal"])

    def test_suggestions_reach_targets_and_keep_hue(self):
        r = tools.contrast_report("#8899cc", "#ffffff")
        for s in r["suggestions"]:
            self.assertGreaterEqual(s["ratio"], s["target"])
            fixed = parse_color(s["color"])
            self.assertGreaterEqual(contrast_ratio(fixed[:3], (255, 255, 255)), s["target"])

    def test_passing_pair_suggestion_unchanged(self):
        r = tools.contrast_report("#000000", "#ffffff")
        self.assertFalse(r["suggestions"][0]["changed"])

    def test_alpha_foreground_is_blended(self):
        r = tools.contrast_report("rgba(0,0,0,0.5)", "#ffffff")
        self.assertAlmostEqual(r["ratio"], 3.95, places=1)

    def test_bad_color(self):
        with self.assertRaises(tools.ColorError) as ctx:
            tools.contrast_report("nope", "#fff")
        self.assertEqual(ctx.exception.field, "fg")
        with self.assertRaises(tools.ColorError) as ctx:
            tools.contrast_report("#fff", "zzz")
        self.assertEqual(ctx.exception.field, "bg")


class Readability(unittest.TestCase):
    def test_easy_vs_hard_russian(self):
        easy, hard = tools.readability(RU_EASY), tools.readability(RU_HARD * 2)
        self.assertEqual(easy["lang"], "ru")
        self.assertGreater(easy["flesch"], hard["flesch"])
        self.assertGreaterEqual(easy["flesch"], 60)
        self.assertTrue(easy["meets_315"])
        self.assertFalse(hard["meets_315"])
        codes = {h["code"] for h in hard["hints"]}
        self.assertIn("hard_text", codes)
        self.assertIn("long_sentences", codes)
        self.assertEqual([h["code"] for h in easy["hints"]], ["good"])

    def test_english_and_grade(self):
        text = "The cat sat on the mat. The dog ran in the park. We like to play games all day. It is a nice and sunny day. " * 3
        r = tools.readability(text)
        self.assertEqual(r["lang"], "en")
        self.assertIsNotNone(r["grade"])
        self.assertGreater(r["flesch"], 80)

    def test_too_short(self):
        r = tools.readability("Слишком мало слов.")
        self.assertFalse(r["enough"])

    def test_text_from_html_skips_noise(self):
        text = tools.text_from_html("<html><head><title>X</title></head><body><nav>Меню</nav><script>var a=1</script><p>Привет, мир.</p><p hidden>Скрыто</p></body></html>")
        self.assertIn("Привет", text)
        for noise in ("Меню", "var a", "Скрыто"):
            self.assertNotIn(noise, text)


class ToolsApi(ApiTestCase):
    def test_contrast_endpoint(self):
        r = self.client.post("/api/tools/contrast", json={"fg": "#595959", "bg": "#fff"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json["checks"]["aaa_normal"])
        bad = self.client.post("/api/tools/contrast", json={"fg": "oops", "bg": "#fff"})
        self.assertEqual(bad.status_code, 422)
        self.assertEqual(bad.json["error"]["details"][0]["field"], "fg")

    def test_readability_endpoint_variants(self):
        self.assertEqual(self.client.post("/api/tools/readability", json={"text": RU_EASY}).status_code, 200)
        self.assertEqual(self.client.post("/api/tools/readability", json={"html": f"<p>{RU_EASY}</p>"}).json["lang"], "ru")
        res = self.make_resource(html=f"<html lang='ru'><title>t</title><body><main><h1>x</h1><p>{RU_EASY}</p></main></body></html>")
        self.assertTrue(self.client.post("/api/tools/readability", json={"resource_id": res["id"]}).json["enough"])
        self.assertEqual(self.client.post("/api/tools/readability", json={}).status_code, 422)
        self.assertEqual(self.client.post("/api/tools/readability", json={"text": "a", "html": "b"}).status_code, 422)
        self.assertEqual(self.client.post("/api/tools/readability", json={"resource_id": 999}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
