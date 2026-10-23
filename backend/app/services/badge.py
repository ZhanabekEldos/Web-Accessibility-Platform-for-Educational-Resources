"""SVG-бейдж с оценкой доступности для вставки на сайт."""
from __future__ import annotations

from html import escape


def _color(score: float | None) -> str:
    # Цвета подобраны так, чтобы белый текст имел контраст не ниже 4,5 : 1.
    if score is None:
        return "#5b6270"
    if score >= 90:
        return "#1b6b3a"
    if score >= 70:
        return "#8a5300"
    return "#b3261e"


def render(label: str, score: float | None, level: str | None) -> str:
    value = "—" if score is None else f"{round(score)}" + (f" · {level}" if level else "")
    lw = 12 + int(len(label) * 6.6)
    vw = 14 + int(len(value) * 7.2)
    w = lw + vw
    text = f"{escape(label)}: {escape(value)}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="22" role="img" aria-label="{text}">'
        f"<title>{text}</title>"
        f'<rect width="{lw}" height="22" rx="4" fill="#2b3040"/>'
        f'<rect x="{lw}" width="{vw}" height="22" rx="4" fill="{_color(score)}"/>'
        f'<rect x="{lw}" width="8" height="22" fill="{_color(score)}"/>'
        f'<g fill="#fff" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11" text-anchor="middle">'
        f'<text x="{lw / 2:.0f}" y="15">{escape(label)}</text>'
        f'<text x="{lw + vw / 2:.0f}" y="15" font-weight="bold">{escape(value)}</text></g></svg>'
    )
