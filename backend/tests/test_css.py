import unittest

from bs4 import BeautifulSoup

from app.a11y.css import StyleEngine, contrast_ratio, parse_color, to_hex


class ColorTests(unittest.TestCase):
    def test_parse_formats(self):
        self.assertEqual(parse_color("#fff"), (255.0, 255.0, 255.0, 1.0))
        self.assertEqual(parse_color("#336699")[:3], (51.0, 102.0, 153.0))
        self.assertEqual(parse_color("rgb(10, 20, 30)")[:3], (10.0, 20.0, 30.0))
        self.assertEqual(parse_color("rgba(0,0,0,.5)")[3], 0.5)
        self.assertEqual(parse_color("red")[:3], (255.0, 0.0, 0.0))
        self.assertEqual(to_hex(parse_color("hsl(120, 100%, 25%)")[:3]), "#008000")
        self.assertIsNone(parse_color("oklch(50% 0.1 20)"))
        self.assertIsNone(parse_color("not-a-color"))

    def test_contrast_reference_values(self):
        self.assertAlmostEqual(contrast_ratio((0, 0, 0), (255, 255, 255)), 21.0, places=2)
        # #767676 на белом — классическая граница 4.5:1
        self.assertAlmostEqual(contrast_ratio((118, 118, 118), (255, 255, 255)), 4.54, places=2)
        self.assertAlmostEqual(contrast_ratio((255, 255, 255), (255, 255, 255)), 1.0)


class EngineTests(unittest.TestCase):
    def engine(self, html):
        soup = BeautifulSoup(html, "html.parser")
        return soup, StyleEngine(soup)

    def test_cascade_specificity_and_inline(self):
        soup, e = self.engine("<style>p{color:red}.a{color:blue}#x{color:green}</style><p id=x class=a style='color:#000'>t</p>")
        self.assertEqual(e.text_color(soup.p)[:3], (0.0, 0.0, 0.0))
        soup, e = self.engine("<style>p{color:red}.a{color:blue}</style><p class=a>t</p>")
        self.assertEqual(e.text_color(soup.p)[:3], (0.0, 0.0, 255.0))

    def test_inheritance_and_variables(self):
        soup, e = self.engine("<html><head><style>:root{--c:#123456}div{color:var(--c);background:#eee}</style></head><body><div><span>t</span></div></body></html>")
        self.assertEqual(to_hex(e.text_color(soup.span)[:3]), "#123456")
        self.assertEqual(to_hex(e.background(soup.span).rgb), "#eeeeee")

    def test_background_image_is_unknown(self):
        soup, e = self.engine("<div style=\"background:url(a.png)\"><p style='color:#fff'>t</p></div>")
        self.assertEqual(e.background(soup.p).status, "image")

    def test_large_text(self):
        soup, e = self.engine("<p style='font-size:24px'>a</p><p style='font-size:19px;font-weight:700'>b</p><p style='font-size:16px'>c</p><h1>d</h1>")
        flags = [e.is_large_text(p) for p in soup.find_all(["p", "h1"])]
        self.assertEqual(flags, [True, True, False, True])


if __name__ == "__main__":
    unittest.main()
