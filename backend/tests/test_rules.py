import unittest

from app.a11y.analyzer import EmptyDocumentError, analyze
from app.a11y.i18n import available_languages, rule_texts
from app.a11y.registry import REGISTRY

FULL = '<!doctype html><html lang="ru"><head><title>Курс</title></head><body>{}</body></html>'
LONG_RU = "Добро пожаловать на курс по высшей математике. " * 6

# Для правил уровня документа и эвристик нужны полные страницы.
BAD_OVERRIDES = {
    "document-title": '<html lang="ru"><head></head><body><main><h1>x</h1></main></body></html>',
    "page-has-h1": '<html lang="ru"><head><title>T</title></head><body><main><h2>Welcome</h2></main></body></html>',
    "landmark-main": '<html lang="ru"><head><title>T</title></head><body><div>text</div></body></html>',
    "bypass-blocks": '<html lang="ru"><head><title>T</title></head><body><nav><a href="/a">a</a></nav><div>Content</div></body></html>',
    "lang-content-mismatch": f'<html lang="en"><head><title>T</title></head><body><p>{LONG_RU}</p></body></html>',
}
MANUAL = {r.id for r in REGISTRY if r.manual}
REVIEW_ONLY_GOOD = {"lang-content-mismatch"}


def hits(rule_id, html):
    result = analyze(html, rules=[REGISTRY.get(rule_id)])
    return [f for f in result.findings if f.rule_id == rule_id]


class RuleExamples(unittest.TestCase):
    """Каждое правило обязано находить свой «плохой» пример и пропускать «хороший»."""

    def test_bad_examples_are_detected(self):
        for rule in REGISTRY:
            with self.subTest(rule=rule.id):
                self.assertTrue(hits(rule.id, BAD_OVERRIDES.get(rule.id, rule.bad)), "плохой пример не найден")

    def test_good_examples_pass(self):
        for rule in REGISTRY:
            if rule.id in MANUAL:
                continue  # ручные правила всегда просят проверку
            with self.subTest(rule=rule.id):
                good = FULL.format(rule.good) if rule.id in BAD_OVERRIDES else rule.good
                self.assertEqual([f for f in hits(rule.id, good) if not f.needs_review], [])

    def test_every_rule_has_texts_in_every_language(self):
        for lang in available_languages():
            for rule in REGISTRY:
                with self.subTest(rule=rule.id, lang=lang):
                    texts = rule_texts(rule.id, lang)
                    self.assertTrue(texts.get("title") and texts.get("message") and texts.get("fix"))

    def test_rule_metadata(self):
        self.assertGreaterEqual(len(REGISTRY), 40)
        self.assertEqual(len({r.id for r in REGISTRY}), len(REGISTRY))
        for rule in REGISTRY:
            self.assertTrue(rule.bad and rule.good, rule.id)


class Behaviour(unittest.TestCase):
    def test_empty_document_rejected(self):
        with self.assertRaises(EmptyDocumentError):
            analyze("   ")

    def test_hidden_content_is_ignored(self):
        html = FULL.format('<main><h1>t</h1><div hidden><img src="a.png"></div><div style="display:none"><img src="b.png"></div></main>')
        self.assertEqual(hits("image-alt", html), [])

    def test_closed_dialog_is_hidden(self):
        closed = FULL.format('<main><h1>t</h1><dialog><img src="a.png"></dialog></main>')
        self.assertEqual(hits("image-alt", closed), [])
        opened = FULL.format('<main><h1>t</h1><dialog open><img src="a.png"></dialog></main>')
        self.assertTrue(hits("image-alt", opened))

    def test_decorative_alt_is_ok(self):
        self.assertEqual(hits("image-alt", FULL.format('<main><img src="a.png" alt=""></main>')), [])

    def test_aria_label_gives_name(self):
        self.assertEqual(hits("button-name", FULL.format('<main><button aria-label="Закрыть">×</button></main>')), [])
        self.assertTrue(hits("button-name", FULL.format("<main><button>  </button></main>")))

    def test_contrast_thresholds(self):
        low = FULL.format('<main><p style="color:#777;background:#fff">text</p></main>')
        self.assertTrue(hits("color-contrast", low))
        ok = FULL.format('<main><p style="color:#595959;background:#fff">text</p></main>')
        self.assertEqual(hits("color-contrast", ok), [])
        large = FULL.format('<main><p style="color:#8a8a8a;background:#fff;font-size:28px">text</p></main>')
        self.assertEqual(hits("color-contrast", large), [])  # 3.4:1 достаточно для крупного текста

    def test_contrast_translucent_color_is_blended(self):
        html = FULL.format('<main><p style="color:rgba(0,0,0,.3);background:#fff">text</p></main>')
        self.assertTrue(hits("color-contrast", html))

    def test_contrast_over_image_needs_review(self):
        html = FULL.format('<main><div style="background:url(x.png)"><p style="color:#fff">text</p></div></main>')
        found = hits("color-contrast", html)
        self.assertTrue(found and all(f.needs_review for f in found))

    def test_findings_limit_and_counts(self):
        imgs = "".join(f'<img src="{i}.png">' for i in range(30))
        result = analyze(FULL.format(f"<main>{imgs}</main>"), rules=[REGISTRY.get("image-alt")], max_findings_per_rule=5)
        self.assertEqual(len(result.findings), 5)
        self.assertEqual(result.summary["violations"], 30)
        self.assertEqual(result.summary["truncated"], {"image-alt": 25})

    def test_fingerprint_is_stable_and_unique(self):
        a = analyze(FULL.format('<main><img src="a.png"><img src="a.png"></main>'), rules=[REGISTRY.get("image-alt")])
        b = analyze(FULL.format('<div><main><img class="x" src="a.png"><img src="a.png"></main></div>'), rules=[REGISTRY.get("image-alt")])
        fa, fb = [f.fingerprint for f in a.findings], [f.fingerprint for f in b.findings]
        self.assertEqual(len(set(fa)), 2)
        self.assertEqual(fa, fb)

    def test_broken_rule_does_not_break_analysis(self):
        from app.a11y.registry import Rule

        def boom(doc, report):
            raise RuntimeError("x")

        broken = Rule("broken", boom, (), "A", "minor", "robust")
        with self.assertLogs("app.a11y.analyzer", level="ERROR"):
            result = analyze(FULL.format("<main></main>"), rules=[broken, REGISTRY.get("image-alt")])
        self.assertEqual(result.summary["rules"]["errors"], ["broken"])

    def test_malformed_html_does_not_crash(self):
        analyze("<div><p>unclosed <b>bold <a href=x>link<table><tr><td>")
        analyze("<<<>>>&&&<img src=" + "a" * 5000 + ">")

    def test_perfect_page_scores_100(self):
        html = FULL.format('<a href="#c">Перейти к содержанию</a><main id="c"><h1>Курс</h1><p>Текст</p></main>')
        result = analyze(html)
        self.assertEqual(result.score, 100.0)
        self.assertEqual(result.level, "AA")


if __name__ == "__main__":
    unittest.main()
