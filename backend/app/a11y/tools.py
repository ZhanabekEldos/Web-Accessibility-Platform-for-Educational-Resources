"""Инструменты вокруг доступности, не связанные со сканированием страницы:
калькулятор контраста с подбором исправленного цвета и анализ читаемости текста.

Модуль чистый (без веба и БД). Тексты подсказок не формируются здесь — возвращаются коды,
перевод делает интерфейс.
"""
from __future__ import annotations

import colorsys
import math
import re
from typing import Any

from bs4 import BeautifulSoup

from .css import blend, contrast_ratio, parse_color, to_hex

# ------------------------------------------------------------------ контраст
THRESHOLDS = {"aa_normal": 4.5, "aa_large": 3.0, "aa_ui": 3.0, "aaa_normal": 7.0, "aaa_large": 4.5}


class ColorError(ValueError):
    """Цвет не удалось разобрать; ``field`` — какое поле (``fg`` или ``bg``)."""

    def __init__(self, field: str) -> None:
        super().__init__(field)
        self.field = field


def _floor2(value: float) -> float:
    # WCAG запрещает округлять вверх: 4.499 не равно 4.5.
    return math.floor(value * 100 + 1e-9) / 100


def _solid(value: str, field: str, over: tuple[float, float, float] = (255, 255, 255)) -> tuple[float, float, float]:
    color = parse_color(value)
    if color is None:
        raise ColorError(field)
    return blend(color, over)


def _shift_lightness(fg: tuple[float, float, float], bg: tuple[float, float, float], target: float, direction: int) -> tuple[float, float, float] | None:
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in fg))
    for step in range(0, 201):
        nl = min(1.0, max(0.0, l + direction * step / 200))
        rgb = tuple(round(c * 255) for c in colorsys.hls_to_rgb(h, nl, s))
        if contrast_ratio(rgb, bg) >= target:  # type: ignore[arg-type]
            return rgb  # type: ignore[return-value]
        if nl in (0.0, 1.0):
            break
    return None


def suggest_foreground(fg: tuple[float, float, float], bg: tuple[float, float, float], target: float) -> tuple[float, float, float] | None:
    """Ближайший к ``fg`` по светлоте цвет (тот же оттенок), дающий контраст не ниже ``target``."""
    if contrast_ratio(fg, bg) >= target:
        return fg
    options = [c for c in (_shift_lightness(fg, bg, target, -1), _shift_lightness(fg, bg, target, 1)) if c is not None]
    if not options:
        return None
    return min(options, key=lambda c: abs(colorsys.rgb_to_hls(*(v / 255 for v in c))[1] - colorsys.rgb_to_hls(*(v / 255 for v in fg))[1]))


def contrast_report(fg_value: str, bg_value: str) -> dict[str, Any]:
    """Контраст пары цветов, прохождение порогов WCAG и исправленные варианты цвета текста."""
    bg = _solid(bg_value, "bg")
    fg = _solid(fg_value, "fg", over=bg)
    ratio = contrast_ratio(fg, bg)
    checks = {key: ratio >= limit for key, limit in THRESHOLDS.items()}
    suggestions = []
    for target in (3.0, 4.5, 7.0):
        fixed = suggest_foreground(fg, bg, target)
        if fixed is not None:
            suggestions.append(
                {"target": target, "color": to_hex(fixed), "ratio": _floor2(contrast_ratio(fixed, bg)), "changed": fixed != fg}
            )
    return {
        "fg": to_hex(fg),
        "bg": to_hex(bg),
        "ratio": _floor2(ratio),
        "checks": checks,
        "suggestions": suggestions,
    }


# ------------------------------------------------------------------ читаемость
_VOWELS_RU = set("аеёиоуыэюя")
_VOWELS_EN = set("aeiouy")
_WORD = re.compile(r"[A-Za-zА-Яа-яЁё]+(?:[-'’][A-Za-zА-Яа-яЁё]+)*")
_SENTENCE_END = re.compile(r"(?<=[.!?…])[\"»”)]*\s+(?=[\"«“(]*[A-ZА-ЯЁ0-9])")
_CYR = re.compile(r"[А-Яа-яЁё]")
_LAT = re.compile(r"[A-Za-z]")
MAX_CHARS = 200_000
LONG_SENTENCE_WORDS = 25


def text_from_html(html: str) -> str:
    """Видимый текст страницы без скриптов, стилей, навигации и скрытых элементов."""
    soup = BeautifulSoup(html, "html.parser")
    for el in soup(["script", "style", "noscript", "template", "svg", "nav", "footer", "head"]):
        el.decompose()
    for el in soup.find_all(attrs={"hidden": True}):
        el.decompose()
    for el in soup.find_all(attrs={"aria-hidden": "true"}):
        el.decompose()
    for block in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "div", "br", "tr", "blockquote"]):
        block.append("\n")
    return re.sub(r"[ \t\r\f\v]+", " ", soup.get_text()).strip()


def detect_language(text: str) -> str:
    cyr, lat = len(_CYR.findall(text)), len(_LAT.findall(text))
    return "ru" if cyr >= lat else "en"


def _syllables(word: str, lang: str) -> int:
    w = word.lower()
    if lang == "ru":
        return max(1, sum(1 for ch in w if ch in _VOWELS_RU))
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    groups = re.findall(r"[aeiouy]+", w)
    return max(1, len(groups))


def _split_sentences(text: str) -> list[str]:
    parts: list[str] = []
    for paragraph in re.split(r"\n+", text):
        paragraph = paragraph.strip()
        if paragraph:
            parts.extend(s.strip() for s in _SENTENCE_END.split(paragraph) if s.strip())
    return parts


def _band(fre: float) -> str:
    for limit, name in ((80, "very_easy"), (70, "easy"), (60, "standard"), (50, "fairly_hard"), (30, "hard")):
        if fre >= limit:
            return name
    return "very_hard"


def readability(text: str, lang: str | None = None) -> dict[str, Any]:
    """Метрики читаемости: индекс Флеша (адаптация Оборневой для русского), длина предложений и слов.

    Для образовательных материалов важно WCAG 3.1.5 (уровень AAA): текст должен быть понятен
    читателю с образованием на уровне неполной средней школы или иметь упрощённую версию.
    """
    text = text[:MAX_CHARS]
    lang = lang if lang in ("ru", "en") else detect_language(text)
    words = _WORD.findall(text)
    sentences = _split_sentences(text)
    if len(words) < 30 or not sentences:
        return {"lang": lang, "words": len(words), "sentences": len(sentences), "enough": False, "hints": [{"code": "too_short", "data": {"min": 30}}]}

    syllables = [_syllables(w, lang) for w in words]
    asl = len(words) / len(sentences)
    asw = sum(syllables) / len(words)
    if lang == "ru":
        fre = 206.835 - 1.52 * asl - 65.14 * asw
        grade = None
        long_word = lambda w, s: s >= 4  # noqa: E731
    else:
        fre = 206.835 - 1.015 * asl - 84.6 * asw
        grade = 0.39 * asl + 11.8 * asw - 15.59
        long_word = lambda w, s: s >= 3  # noqa: E731
    fre = max(0.0, min(100.0, fre))
    long_words = [w for w, s in zip(words, syllables) if long_word(w, s)]
    long_sentences = []
    for sentence in sentences:
        count = len(_WORD.findall(sentence))
        if count > LONG_SENTENCE_WORDS:
            long_sentences.append({"words": count, "text": sentence if len(sentence) <= 280 else sentence[:277] + "…"})
    long_sentences.sort(key=lambda s: -s["words"])
    long_share = len(long_words) / len(words)

    hints: list[dict[str, Any]] = []
    if fre < 50:
        hints.append({"code": "hard_text", "data": {"fre": round(fre)}})
    if long_sentences:
        hints.append({"code": "long_sentences", "data": {"count": len(long_sentences), "limit": LONG_SENTENCE_WORDS}})
    if long_share > 0.25:
        hints.append({"code": "long_words", "data": {"share": round(long_share * 100)}})
    if asl > 20 and not long_sentences:
        hints.append({"code": "avg_sentence", "data": {"asl": round(asl, 1)}})
    if not hints:
        hints.append({"code": "good", "data": {}})

    return {
        "lang": lang,
        "enough": True,
        "words": len(words),
        "sentences": len(sentences),
        "characters": len(text),
        "avg_sentence_words": round(asl, 1),
        "avg_syllables": round(asw, 2),
        "long_words_share": round(long_share * 100, 1),
        "flesch": round(fre, 1),
        "band": _band(fre),
        "grade": round(grade, 1) if grade is not None else None,
        "reading_minutes": max(1, round(len(words) / (180 if lang == "ru" else 220))),
        "top_long_words": sorted({w.lower() for w in long_words}, key=lambda w: (-len(w), w))[:12],
        "long_sentences": long_sentences[:5],
        "hints": hints,
        "meets_315": fre >= 60,  # ориентир для критерия 3.1.5 (AAA)
    }
