"""Чек-лист ручного аудита: то, что автоматика проверить не может.

Каждый пункт — ``id``, принцип POUR, критерии WCAG и тексты (ru/en): что проверить и как.
Чтобы добавить пункт, допишите его в ``ITEMS``; тест ``test_audit`` проверит полноту переводов и критерии.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .wcag import CATALOG


@dataclass(frozen=True, slots=True)
class Item:
    id: str
    principle: str
    wcag: tuple[str, ...]
    ru: tuple[str, str]  # (что проверить, как проверить)
    en: tuple[str, str]
    education: bool = False  # специфично для учебных материалов


ITEMS: tuple[Item, ...] = (
    # --- воспринимаемость
    Item("alt-meaning", "perceivable", ("1.1.1",),
         ("Описания изображений передают смысл, а не просто «картинка»", "Отключите картинки или прослушайте страницу скринридером: понятно ли, что на графике, схеме, фото?"),
         ("Image descriptions convey meaning, not just “picture”", "Turn images off or listen with a screen reader: is it clear what the chart, diagram or photo shows?")),
    Item("captions", "perceivable", ("1.2.2",),
         ("У каждого видео есть точные субтитры", "Включите видео без звука: можно ли понять речь и важные звуки по субтитрам?"),
         ("Every video has accurate captions", "Play the video muted: can you follow speech and key sounds from captions?"), True),
    Item("transcript", "perceivable", ("1.2.1",),
         ("У аудио и подкастов есть текстовая расшифровка", "Найдите ссылку на расшифровку рядом с плеером."),
         ("Audio and podcasts have a text transcript", "Look for a transcript link next to the player."), True),
    Item("audio-description", "perceivable", ("1.2.5",),
         ("Важное визуальное содержание видео озвучено (аудиоописание)", "Прослушайте видео с закрытыми глазами: понятно ли, что показывают на экране?"),
         ("Important visual content of videos is narrated (audio description)", "Listen to the video with eyes closed: is it clear what is shown on screen?"), True),
    Item("color-only", "perceivable", ("1.4.1",),
         ("Смысл не передаётся только цветом", "Переключите экран в оттенки серого: различимы ли ошибки, статусы, обязательные поля, ссылки?"),
         ("Meaning is not conveyed by color alone", "Switch the screen to grayscale: are errors, statuses, required fields and links still distinguishable?")),
    Item("zoom", "perceivable", ("1.4.4", "1.4.10"),
         ("Страница удобна при увеличении до 200 % и 400 %", "Увеличьте масштаб браузера до 400 %: нет горизонтальной прокрутки, текст не обрезан, ничего не перекрывается."),
         ("The page works at 200% and 400% zoom", "Zoom the browser to 400%: no horizontal scrolling, nothing clipped or overlapping.")),
    Item("text-spacing", "perceivable", ("1.4.12",),
         ("Текст выдерживает увеличенные интервалы", "Примените расширение Text Spacing: содержимое не обрезается и не накладывается."),
         ("Text survives increased spacing", "Apply a text-spacing bookmarklet: content is not clipped or overlapped.")),
    Item("contrast-hard-cases", "perceivable", ("1.4.3", "1.4.11"),
         ("Достаточен контраст там, где автоматика не видит: текст на картинках и градиентах, границы полей, иконки", "Проверьте пипеткой в инструменте «Контраст»: текст — 4,5 : 1, значки и границы — 3 : 1."),
         ("Contrast is sufficient where automation cannot see: text over images and gradients, field borders, icons", "Sample colors with the Contrast tool: text 4.5:1, icons and borders 3:1.")),
    # --- управляемость
    Item("keyboard-all", "operable", ("2.1.1",),
         ("Всё работает только с клавиатуры", "Пройдите страницу клавишами Tab, Shift+Tab, Enter, пробел, стрелки; мышь не используйте."),
         ("Everything works with the keyboard alone", "Walk through with Tab, Shift+Tab, Enter, Space and arrows; do not use the mouse.")),
    Item("no-trap", "operable", ("2.1.2",),
         ("Нет «ловушек» клавиатурного фокуса", "Из встроенного плеера, окна и редактора можно выйти с клавиатуры."),
         ("No keyboard focus traps", "You can leave embedded players, dialogs and editors using the keyboard.")),
    Item("focus-visible", "operable", ("2.4.7", "2.4.3"),
         ("Фокус всегда виден, порядок обхода логичен", "При Tab рамка фокуса заметна; порядок совпадает с визуальным."),
         ("Focus is always visible and the order is logical", "The focus ring is obvious when tabbing; order matches the visual layout.")),
    Item("timing", "operable", ("2.2.1",),
         ("Ограничение времени (тесты, сессии) можно отключить или продлить", "Найдите таймеры тестов и автовыход: есть ли способ увеличить время?"),
         ("Time limits (quizzes, sessions) can be turned off or extended", "Find quiz timers and auto-logout: is there a way to extend them?"), True),
    Item("motion", "operable", ("2.2.2", "2.3.1"),
         ("Анимацию можно остановить; нет вспышек чаще трёх в секунду", "Проверьте карусели, автоплей, бегущие строки."),
         ("Animation can be paused; nothing flashes more than three times per second", "Check carousels, autoplay and tickers.")),
    Item("target-size", "operable", ("2.5.8",),
         ("Элементы управления достаточно крупные для касания (от 24 × 24 px)", "Проверьте на телефоне: можно ли попасть пальцем в кнопки и ссылки, не задев соседние."),
         ("Controls are large enough to tap (at least 24×24 px)", "Try on a phone: can you hit buttons and links without touching neighbours?")),
    # --- понятность
    Item("plain-language", "understandable", ("3.1.3", "3.1.5"),
         ("Текст понятен целевой аудитории; термины и сокращения объяснены", "Запустите инструмент «Читаемость»; найдите термины без определений."),
         ("Text suits the audience; terms and abbreviations are explained", "Run the Readability tool; look for terms without definitions."), True),
    Item("lang-parts", "understandable", ("3.1.2",),
         ("Вставки на другом языке размечены атрибутом lang", "Цитаты и термины на иностранном языке озвучиваются скринридером с правильным произношением."),
         ("Passages in another language are marked with lang", "Foreign quotes and terms are pronounced correctly by a screen reader.")),
    Item("consistent-nav", "understandable", ("3.2.3",),
         ("Навигация единообразна на всех страницах курса", "Меню, поиск и кнопка «Назад» находятся в одном месте на разных страницах."),
         ("Navigation is consistent across course pages", "Menu, search and “Back” appear in the same place on different pages."), True),
    Item("error-help", "understandable", ("3.3.1", "3.3.3"),
         ("Ошибки в формах и тестах объяснены и подсказывают, как исправить", "Отправьте форму с ошибкой: сообщение озвучивается и понятно."),
         ("Form and quiz errors are explained and suggest a fix", "Submit a form with an error: the message is announced and understandable."), True),
    # --- надёжность
    Item("screenreader", "robust", ("4.1.2",),
         ("Страница проходится скринридером без потери смысла", "Пройдите ключевой сценарий в NVDA (Windows) или VoiceOver (macOS/iOS)."),
         ("The page works with a screen reader without losing meaning", "Complete the key task in NVDA (Windows) or VoiceOver (macOS/iOS).")),
    Item("status-messages", "robust", ("4.1.3",),
         ("Динамические сообщения (результат теста, загрузка, ошибка) озвучиваются", "Проверьте, что скринридер сообщает о результате без перевода фокуса."),
         ("Dynamic messages (quiz result, loading, error) are announced", "Check that a screen reader announces the result without moving focus."), True),
    Item("documents", "robust", ("1.3.1",),
         ("PDF, Word и презентации к занятию тоже доступны (теги, заголовки, описания)", "Откройте файл в проверке доступности редактора/Acrobat; проверьте порядок чтения."),
         ("PDFs, Word files and slides are accessible too (tags, headings, descriptions)", "Run the editor's/Acrobat's accessibility checker; verify reading order."), True),
    Item("math", "robust", ("1.1.1", "1.3.1"),
         ("Формулы и химические записи доступны (MathML/LaTeX с текстовой записью)", "Скринридер читает формулу осмысленно, а не по символам и не как картинку."),
         ("Formulas and chemical notation are accessible (MathML/LaTeX with text form)", "A screen reader reads the formula meaningfully, not as images or loose symbols."), True),
)

BY_ID: dict[str, Item] = {i.id: i for i in ITEMS}
STATUSES = ("pass", "fail", "na")


def catalog(lang: str) -> list[dict[str, Any]]:
    out = []
    for item in ITEMS:
        title, how = item.ru if lang == "ru" else item.en
        out.append(
            {
                "id": item.id,
                "principle": item.principle,
                "title": title,
                "how": how,
                "education": item.education,
                "wcag": [CATALOG[sc].as_dict() for sc in item.wcag],
            }
        )
    return out
