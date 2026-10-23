"""Мини-движок CSS для проверок контраста и размера текста.

Это сознательно упрощённая реализация: она понимает цвета (hex/rgb/hsl/имена),
наследование, каскад «встроенные стили → таблицы стилей по специфичности»,
CSS-переменные ``var(--x)``, сокращения ``background`` и ``font``.
Не поддерживаются медиазапросы, псевдоклассы состояния, ``opacity``,
``color-mix()``/``oklch()``. Если что-то определить нельзя, проверка
не выдаёт ложных нарушений, а пропускает элемент или просит ручную проверку.
"""
from __future__ import annotations

import colorsys
import re
from dataclasses import dataclass
from typing import Iterator

from bs4 import BeautifulSoup, Tag

Color = tuple[float, float, float, float]  # r, g, b (0-255), alpha (0-1)
RGB = tuple[float, float, float]

_NAMED_RAW = """
aliceblue f0f8ff antiquewhite faebd7 aqua 00ffff aquamarine 7fffd4 azure f0ffff beige f5f5dc bisque ffe4c4
black 000000 blanchedalmond ffebcd blue 0000ff blueviolet 8a2be2 brown a52a2a burlywood deb887 cadetblue 5f9ea0
chartreuse 7fff00 chocolate d2691e coral ff7f50 cornflowerblue 6495ed cornsilk fff8dc crimson dc143c cyan 00ffff
darkblue 00008b darkcyan 008b8b darkgoldenrod b8860b darkgray a9a9a9 darkgreen 006400 darkgrey a9a9a9
darkkhaki bdb76b darkmagenta 8b008b darkolivegreen 556b2f darkorange ff8c00 darkorchid 9932cc darkred 8b0000
darksalmon e9967a darkseagreen 8fbc8f darkslateblue 483d8b darkslategray 2f4f4f darkslategrey 2f4f4f
darkturquoise 00ced1 darkviolet 9400d3 deeppink ff1493 deepskyblue 00bfff dimgray 696969 dimgrey 696969
dodgerblue 1e90ff firebrick b22222 floralwhite fffaf0 forestgreen 228b22 fuchsia ff00ff gainsboro dcdcdc
ghostwhite f8f8ff gold ffd700 goldenrod daa520 gray 808080 green 008000 greenyellow adff2f grey 808080
honeydew f0fff0 hotpink ff69b4 indianred cd5c5c indigo 4b0082 ivory fffff0 khaki f0e68c lavender e6e6fa
lavenderblush fff0f5 lawngreen 7cfc00 lemonchiffon fffacd lightblue add8e6 lightcoral f08080 lightcyan e0ffff
lightgoldenrodyellow fafad2 lightgray d3d3d3 lightgreen 90ee90 lightgrey d3d3d3 lightpink ffb6c1
lightsalmon ffa07a lightseagreen 20b2aa lightskyblue 87cefa lightslategray 778899 lightslategrey 778899
lightsteelblue b0c4de lightyellow ffffe0 lime 00ff00 limegreen 32cd32 linen faf0e6 magenta ff00ff maroon 800000
mediumaquamarine 66cdaa mediumblue 0000cd mediumorchid ba55d3 mediumpurple 9370db mediumseagreen 3cb371
mediumslateblue 7b68ee mediumspringgreen 00fa9a mediumturquoise 48d1cc mediumvioletred c71585
midnightblue 191970 mintcream f5fffa mistyrose ffe4e1 moccasin ffe4b5 navajowhite ffdead navy 000080
oldlace fdf5e6 olive 808000 olivedrab 6b8e23 orange ffa500 orangered ff4500 orchid da70d6 palegoldenrod eee8aa
palegreen 98fb98 paleturquoise afeeee palevioletred db7093 papayawhip ffefd5 peachpuff ffdab9 peru cd853f
pink ffc0cb plum dda0dd powderblue b0e0e6 purple 800080 rebeccapurple 663399 red ff0000 rosybrown bc8f8f
royalblue 4169e1 saddlebrown 8b4513 salmon fa8072 sandybrown f4a460 seagreen 2e8b57 seashell fff5ee
sienna a0522d silver c0c0c0 skyblue 87ceeb slateblue 6a5acd slategray 708090 slategrey 708090 snow fffafa
springgreen 00ff7f steelblue 4682b4 tan d2b48c teal 008080 thistle d8bfd8 tomato ff6347 turquoise 40e0d0
violet ee82ee wheat f5deb3 white ffffff whitesmoke f5f5f5 yellow ffff00 yellowgreen 9acd32
"""
NAMED_COLORS: dict[str, str] = dict(zip(_NAMED_RAW.split()[0::2], _NAMED_RAW.split()[1::2]))

_HEX_RE = re.compile(r"^#([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})$")
_FUNC_RE = re.compile(r"^(rgba?|hsla?)\((.*)\)$")
_SPLIT_ARGS = re.compile(r"[\s,/]+")


# --------------------------------------------------------------------------- цвета
def parse_color(value: str | None) -> Color | None:
    """Разбирает CSS-цвет. Возвращает ``None``, если формат не поддерживается."""
    if not value:
        return None
    v = value.strip().lower()
    if v == "transparent":
        return (0.0, 0.0, 0.0, 0.0)
    if v in NAMED_COLORS:
        return _from_hex(NAMED_COLORS[v])
    m = _HEX_RE.match(v)
    if m:
        return _from_hex(m.group(1))
    m = _FUNC_RE.match(v)
    if m:
        return _from_func(m.group(1), m.group(2))
    return None


def _from_hex(h: str) -> Color:
    if len(h) in (3, 4):
        h = "".join(ch * 2 for ch in h)
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    return (float(r), float(g), float(b), round(a, 3))


def _num(token: str, scale: float) -> float | None:
    try:
        if token.endswith("%"):
            return float(token[:-1]) / 100 * scale
        return float(token)
    except ValueError:
        return None


def _from_func(kind: str, inner: str) -> Color | None:
    args = [a for a in _SPLIT_ARGS.split(inner.strip()) if a]
    if len(args) not in (3, 4):
        return None
    alpha = 1.0
    if len(args) == 4:
        a = _num(args[3], 1.0)
        if a is None:
            return None
        alpha = max(0.0, min(1.0, a))
    if kind.startswith("rgb"):
        vals = [_num(a, 255.0) for a in args[:3]]
        if any(v is None for v in vals):
            return None
        r, g, b = (max(0.0, min(255.0, v)) for v in vals)  # type: ignore[type-var]
        return (r, g, b, alpha)
    # hsl
    hue_raw = args[0].removesuffix("deg")
    try:
        hue = float(hue_raw) % 360 / 360
    except ValueError:
        return None
    sat, light = _num(args[1], 1.0), _num(args[2], 1.0)
    if sat is None or light is None:
        return None
    r, g, b = colorsys.hls_to_rgb(hue, max(0.0, min(1.0, light)), max(0.0, min(1.0, sat)))
    return (r * 255, g * 255, b * 255, alpha)


def blend(fg: Color, bg: RGB) -> RGB:
    """Накладывает полупрозрачный цвет ``fg`` на непрозрачный фон ``bg``."""
    a = fg[3]
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3))  # type: ignore[return-value]


def relative_luminance(rgb: RGB) -> float:
    def channel(c: float) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: RGB, b: RGB) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def to_hex(rgb: RGB) -> str:
    return "#" + "".join(f"{round(max(0, min(255, c))):02x}" for c in rgb)


# --------------------------------------------------------------------------- разбор CSS
_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
_RELEVANT = {
    "color", "background", "background-color", "background-image",
    "font-size", "font-weight", "font", "display", "visibility",
}
_WORD_SIZES = {
    "xx-small": 9.0, "x-small": 10.0, "small": 13.0, "medium": 16.0,
    "large": 18.0, "x-large": 24.0, "xx-large": 32.0, "xxx-large": 48.0,
}
_TAG_FONT_SCALE = {"h1": 2.0, "h2": 1.5, "h3": 1.17, "h4": 1.0, "h5": 0.83, "h6": 0.67, "small": 0.83, "sub": 0.83, "sup": 0.83}
_BOLD_TAGS = {"b", "strong", "th", "h1", "h2", "h3", "h4", "h5", "h6"}
_SIZE_RE = re.compile(r"^(\d*\.?\d+)(px|pt|em|rem|%|vw|vh)?$")
_VAR_RE = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*))?\)")


def strip_comments(css: str) -> str:
    return _COMMENT_RE.sub("", css)


def split_top_level(text: str, sep: str) -> list[str]:
    """Делит строку по ``sep``, не разрывая скобки и кавычки."""
    parts: list[str] = []
    depth, quote, start = 0, "", 0
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == sep and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return parts


def parse_declarations(text: str) -> list[tuple[str, str, bool]]:
    """``color: red !important; --x: 1`` → ``[(prop, value, important), ...]``."""
    result: list[tuple[str, str, bool]] = []
    for chunk in split_top_level(strip_comments(text), ";"):
        if ":" not in chunk:
            continue
        prop, _, value = chunk.partition(":")
        prop = prop.strip().lower() if not prop.strip().startswith("--") else prop.strip()
        value = value.strip()
        important = bool(re.search(r"!\s*important\s*$", value, re.I))
        if important:
            value = re.sub(r"!\s*important\s*$", "", value, flags=re.I).strip()
        if prop and value:
            result.append((prop, value, important))
    return result


def iter_rules(css: str) -> Iterator[tuple[str, str]]:
    """Возвращает пары (селектор, блок деклараций) для обычных правил верхнего уровня.

    At-правила (``@media``, ``@supports``, ``@font-face`` ...) пропускаются целиком.
    """
    css = strip_comments(css)
    i, n = 0, len(css)
    while i < n:
        brace = css.find("{", i)
        if brace == -1:
            return
        prelude = css[i:brace].rsplit(";", 1)[-1].strip()
        depth, j = 1, brace + 1
        while j < n and depth:
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
            j += 1
        body = css[brace + 1 : j - 1]
        i = j
        if prelude and not prelude.startswith("@"):
            yield prelude, body


def specificity(selector: str) -> int:
    ids = len(re.findall(r"#[\w-]+", selector))
    classes = len(re.findall(r"\.[\w-]+|\[[^\]]+\]|:(?!:)(?!not\(|is\(|where\()[\w-]+", selector))
    types = len(re.findall(r"(?:^|[\s>+~(])[a-zA-Z][\w-]*", selector))
    return ids * 10_000 + classes * 100 + types


# --------------------------------------------------------------------------- движок
@dataclass(frozen=True, slots=True)
class Background:
    rgb: RGB | None
    status: str  # ok | image | unknown
    node: Tag | None = None  # предок, чей фон нельзя вычислить (для status != ok)


class StyleEngine:
    """Лениво вычисляет нужные для проверок свойства элементов документа."""

    LINK_COLOR: Color = (0.0, 0.0, 238.0, 1.0)

    def __init__(self, soup: BeautifulSoup, *, max_rules: int = 2000) -> None:
        self._soup = soup
        self._max_rules = max_rules
        self._entries: dict[int, list[tuple[tuple[int, int, int, int], str, str]]] = {}
        self._declared: dict[int, dict[str, str]] = {}
        self._font_cache: dict[int, float] = {}
        self.has_color_rules = False
        self._build()

    # -- построение таблицы объявлений ------------------------------------------------
    def _add(self, el: Tag, key: tuple[int, int, int, int], prop: str, value: str) -> None:
        for p, v in self._expand(prop, value):
            self._entries.setdefault(id(el), []).append((key, p, v))
            if p in ("color", "background-color", "background-image"):
                self.has_color_rules = True

    def _build(self) -> None:
        order = 0
        for style in self._soup.find_all("style"):
            media = (style.get("media") or "all").lower()
            if "print" in media and "screen" not in media and "all" not in media:
                continue
            for selector_text, body in iter_rules(style.get_text()):
                decls = [d for d in parse_declarations(body) if d[0] in _RELEVANT or d[0].startswith("--")]
                if not decls:
                    continue
                for selector in split_top_level(selector_text, ","):
                    selector = selector.strip()
                    if not selector or order >= self._max_rules:
                        continue
                    order += 1
                    try:
                        matched = self._soup.select(selector)
                    except Exception:  # noqa: BLE001 — неподдерживаемый селектор, пропускаем
                        continue
                    spec = specificity(selector)
                    for el in matched:
                        for prop, value, important in decls:
                            self._add(el, (int(important), 0, spec, order), prop, value)
        for el in self._soup.find_all(style=True):
            for prop, value, important in parse_declarations(el.get("style", "")):
                if prop in _RELEVANT or prop.startswith("--"):
                    self._add(el, (int(important), 1, 0, 0), prop, value)

    @staticmethod
    def _expand(prop: str, value: str) -> list[tuple[str, str]]:
        """Раскрывает сокращения ``background`` и ``font``."""
        if prop == "background":
            color = "transparent"
            image = "none"
            for token in split_top_level(value, " "):
                token = token.strip()
                if not token:
                    continue
                if "gradient(" in token or token.startswith("url("):
                    image = token
                elif parse_color(token) is not None or token.startswith("var("):
                    color = token
            return [("background-color", color), ("background-image", image)]
        if prop == "font":
            out: list[tuple[str, str]] = []
            for token in split_top_level(value, " "):
                token = token.split("/")[0].strip().lower()
                if token in ("bold", "bolder") or re.fullmatch(r"[1-9]00", token):
                    out.append(("font-weight", token))
                elif _SIZE_RE.match(token) or token in _WORD_SIZES:
                    out.append(("font-size", token))
            return out
        return [(prop, value)]

    # -- доступ к значениям ---------------------------------------------------------
    def declared(self, el: Tag) -> dict[str, str]:
        key = id(el)
        cached = self._declared.get(key)
        if cached is not None:
            return cached
        best: dict[str, tuple[tuple[int, int, int, int], str]] = {}
        for rank, prop, value in self._entries.get(key, ()):
            if prop not in best or rank >= best[prop][0]:
                best[prop] = (rank, value)
        result = {p: v for p, (_, v) in best.items()}
        self._declared[key] = result
        return result

    def value(self, el: Tag, prop: str) -> str | None:
        raw = self.declared(el).get(prop)
        return self._resolve_vars(el, raw) if raw is not None else None

    def _resolve_vars(self, el: Tag, value: str, depth: int = 0) -> str | None:
        if "var(" not in value:
            return value
        if depth > 5:
            return None

        def repl(match: re.Match[str]) -> str:
            found = self._custom_property(el, match.group(1), depth + 1)
            if found is None:
                found = match.group(2).strip() if match.group(2) else None
            return found if found is not None else "\0"

        resolved = _VAR_RE.sub(repl, value)
        return None if "\0" in resolved else resolved

    def _custom_property(self, el: Tag, name: str, depth: int) -> str | None:
        node: Tag | None = el
        while isinstance(node, Tag):
            raw = self.declared(node).get(name)
            if raw is not None:
                return self._resolve_vars(node, raw, depth)
            node = node.parent if isinstance(node.parent, Tag) else None
        return None

    # -- производные величины -----------------------------------------------------------
    def is_display_none(self, el: Tag) -> bool:
        display = (self.value(el, "display") or "").lower()
        visibility = (self.value(el, "visibility") or "").lower()
        return display == "none" or visibility == "hidden"

    def text_color(self, el: Tag) -> Color | None:
        """Цвет текста с учётом наследования; ``None`` — определить не удалось."""
        node: Tag | None = el
        while isinstance(node, Tag):
            raw = self.value(node, "color")
            if raw is not None:
                low = raw.strip().lower()
                if low in ("inherit", "unset", "currentcolor"):
                    node = node.parent if isinstance(node.parent, Tag) else None
                    continue
                if low == "initial":
                    return (0.0, 0.0, 0.0, 1.0)
                return parse_color(raw)
            if node.name == "a" and node.has_attr("href"):
                return self.LINK_COLOR
            node = node.parent if isinstance(node.parent, Tag) else None
        return (0.0, 0.0, 0.0, 1.0)

    def background(self, el: Tag) -> Background:
        """Фон под текстом: ближайший непрозрачный цвет предков (по умолчанию белый)."""
        layers: list[Color] = []
        node: Tag | None = el
        while isinstance(node, Tag):
            image = (self.value(node, "background-image") or "none").lower()
            if image not in ("none", "initial", "unset") and ("url(" in image or "gradient(" in image):
                return Background(None, "image", node)
            raw = self.value(node, "background-color")
            if raw is not None:
                low = raw.strip().lower()
                if low not in ("inherit", "initial", "unset", "transparent"):
                    color = parse_color(raw)
                    if color is None:
                        return Background(None, "unknown", node)
                    if color[3] >= 0.999:
                        base: RGB = color[:3]
                        for layer in reversed(layers):
                            base = blend(layer, base)
                        return Background(base, "ok")
                    if color[3] > 0:
                        layers.append(color)
            node = node.parent if isinstance(node.parent, Tag) else None
        base = (255.0, 255.0, 255.0)
        for layer in reversed(layers):
            base = blend(layer, base)
        return Background(base, "ok")

    def font_size_px(self, el: Tag) -> float:
        key = id(el)
        cached = self._font_cache.get(key)
        if cached is not None:
            return cached
        parent = el.parent if isinstance(el.parent, Tag) else None
        parent_size = self.font_size_px(parent) if parent is not None and parent.name != "[document]" else 16.0
        size = parent_size * _TAG_FONT_SCALE.get(el.name, 1.0)
        raw = self.value(el, "font-size")
        if raw:
            parsed = self._parse_size(raw.strip().lower(), parent_size)
            if parsed is not None:
                size = parsed
        self._font_cache[key] = size
        return size

    @staticmethod
    def _parse_size(raw: str, parent: float) -> float | None:
        if raw in _WORD_SIZES:
            return _WORD_SIZES[raw]
        if raw == "larger":
            return parent * 1.2
        if raw == "smaller":
            return parent / 1.2
        m = _SIZE_RE.match(raw)
        if not m:
            return None
        number, unit = float(m.group(1)), m.group(2) or "px"
        if unit == "px":
            return number
        if unit == "pt":
            return number * 4 / 3
        if unit == "em":
            return number * parent
        if unit == "rem":
            return number * 16
        if unit == "%":
            return number / 100 * parent
        return None  # vw/vh — зависит от окна

    def is_bold(self, el: Tag) -> bool:
        node: Tag | None = el
        while isinstance(node, Tag):
            raw = (self.value(node, "font-weight") or "").strip().lower()
            if raw in ("bold", "bolder"):
                return True
            if raw.isdigit():
                return int(raw) >= 700
            if raw in ("normal", "lighter"):
                return False
            if node.name in _BOLD_TAGS:
                return True
            node = node.parent if isinstance(node.parent, Tag) else None
        return False

    def is_large_text(self, el: Tag) -> bool:
        size = self.font_size_px(el)
        return size >= 24.0 or (size >= 18.66 and self.is_bold(el))
