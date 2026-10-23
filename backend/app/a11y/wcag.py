"""Каталог критериев успеха WCAG 2.2, на которые ссылаются правила.

Добавляя правило с новым критерием, допишите его сюда — реестр проверяет,
что каждый указанный в правиле критерий существует.
"""
from __future__ import annotations

from dataclasses import dataclass

WCAG_VERSION = "2.2"
_BASE_URL = "https://www.w3.org/WAI/WCAG22/Understanding/"


@dataclass(frozen=True, slots=True)
class SuccessCriterion:
    id: str
    name: str
    level: str  # A | AA | AAA
    principle: str
    slug: str

    @property
    def url(self) -> str:
        return f"{_BASE_URL}{self.slug}.html"

    def as_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "level": self.level, "url": self.url}


_CRITERIA = (
    SuccessCriterion("1.1.1", "Non-text Content", "A", "perceivable", "non-text-content"),
    SuccessCriterion("1.2.1", "Audio-only and Video-only (Prerecorded)", "A", "perceivable", "audio-only-and-video-only-prerecorded"),
    SuccessCriterion("1.2.2", "Captions (Prerecorded)", "A", "perceivable", "captions-prerecorded"),
    SuccessCriterion("1.2.5", "Audio Description (Prerecorded)", "AA", "perceivable", "audio-description-prerecorded"),
    SuccessCriterion("1.3.1", "Info and Relationships", "A", "perceivable", "info-and-relationships"),
    SuccessCriterion("1.3.5", "Identify Input Purpose", "AA", "perceivable", "identify-input-purpose"),
    SuccessCriterion("1.4.1", "Use of Color", "A", "perceivable", "use-of-color"),
    SuccessCriterion("1.4.2", "Audio Control", "A", "perceivable", "audio-control"),
    SuccessCriterion("1.4.3", "Contrast (Minimum)", "AA", "perceivable", "contrast-minimum"),
    SuccessCriterion("1.4.4", "Resize Text", "AA", "perceivable", "resize-text"),
    SuccessCriterion("1.4.10", "Reflow", "AA", "perceivable", "reflow"),
    SuccessCriterion("1.4.11", "Non-text Contrast", "AA", "perceivable", "non-text-contrast"),
    SuccessCriterion("1.4.12", "Text Spacing", "AA", "perceivable", "text-spacing"),
    SuccessCriterion("2.1.1", "Keyboard", "A", "operable", "keyboard"),
    SuccessCriterion("2.1.2", "No Keyboard Trap", "A", "operable", "no-keyboard-trap"),
    SuccessCriterion("2.2.1", "Timing Adjustable", "A", "operable", "timing-adjustable"),
    SuccessCriterion("2.2.2", "Pause, Stop, Hide", "A", "operable", "pause-stop-hide"),
    SuccessCriterion("2.3.1", "Three Flashes or Below Threshold", "A", "operable", "three-flashes-or-below-threshold"),
    SuccessCriterion("2.4.1", "Bypass Blocks", "A", "operable", "bypass-blocks"),
    SuccessCriterion("2.4.2", "Page Titled", "A", "operable", "page-titled"),
    SuccessCriterion("2.4.3", "Focus Order", "A", "operable", "focus-order"),
    SuccessCriterion("2.4.4", "Link Purpose (In Context)", "A", "operable", "link-purpose-in-context"),
    SuccessCriterion("2.4.6", "Headings and Labels", "AA", "operable", "headings-and-labels"),
    SuccessCriterion("2.4.7", "Focus Visible", "AA", "operable", "focus-visible"),
    SuccessCriterion("2.5.8", "Target Size (Minimum)", "AA", "operable", "target-size-minimum"),
    SuccessCriterion("3.1.1", "Language of Page", "A", "understandable", "language-of-page"),
    SuccessCriterion("3.1.2", "Language of Parts", "AA", "understandable", "language-of-parts"),
    SuccessCriterion("3.1.3", "Unusual Words", "AAA", "understandable", "unusual-words"),
    SuccessCriterion("3.1.5", "Reading Level", "AAA", "understandable", "reading-level"),
    SuccessCriterion("3.2.3", "Consistent Navigation", "AA", "understandable", "consistent-navigation"),
    SuccessCriterion("3.3.1", "Error Identification", "A", "understandable", "error-identification"),
    SuccessCriterion("3.3.2", "Labels or Instructions", "A", "understandable", "labels-or-instructions"),
    SuccessCriterion("3.3.3", "Error Suggestion", "AA", "understandable", "error-suggestion"),
    SuccessCriterion("4.1.2", "Name, Role, Value", "A", "robust", "name-role-value"),
    SuccessCriterion("4.1.3", "Status Messages", "AA", "robust", "status-messages"),
)

CATALOG: dict[str, SuccessCriterion] = {sc.id: sc for sc in _CRITERIA}
