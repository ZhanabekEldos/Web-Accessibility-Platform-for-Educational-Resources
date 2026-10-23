"""Оценка доступности по результатам правил.

Принципы расчёта (чтобы оценке можно было доверять и её можно было объяснить):

* В оценке участвуют только применимые автоматические правила: если на странице нет
  видео, правила про субтитры ничего не добавляют и не отнимают.
* Каждое правило весит по серьёзности (critical 10 · serious 7 · moderate 3 · minor 1).
* Правило без нарушений даёт полный балл. Если нарушения есть, начисляется частичный
  балл — не более ``PARTIAL_CREDIT_CAP`` и тем меньше, чем больше доля нарушивших
  элементов. Так оценка растёт по мере исправления, но правило с ошибкой
  не может «перетянуть» страницу к 100.
* Замечания «проверить вручную» и ручные правила в оценку не входят.
"""
from __future__ import annotations

from dataclasses import dataclass

from .registry import PRINCIPLES, Rule

PARTIAL_CREDIT_CAP = 0.5


@dataclass(slots=True)
class RuleResult:
    rule: Rule
    applicable: int
    violations: int
    reviews: int


def rule_score(result: RuleResult) -> float | None:
    """Балл правила от 0 до 1 или ``None``, если правило в оценке не участвует."""
    if result.rule.manual or result.applicable <= 0:
        return None
    if result.violations == 0:
        return 1.0
    ratio = min(1.0, result.violations / result.applicable)
    return (1.0 - ratio) * PARTIAL_CREDIT_CAP


def weighted_score(results: list[RuleResult], principle: str | None = None) -> float | None:
    numerator = denominator = 0.0
    for r in results:
        if principle is not None and r.rule.principle != principle:
            continue
        score = rule_score(r)
        if score is None:
            continue
        numerator += r.rule.weight * score
        denominator += r.rule.weight
    if denominator == 0:
        return None
    return round(100.0 * numerator / denominator, 1)


def principle_scores(results: list[RuleResult]) -> dict[str, float | None]:
    return {p: weighted_score(results, p) for p in PRINCIPLES}


def conformance_level(results: list[RuleResult]) -> str | None:
    """Наивысший уровень WCAG (A или AA), по которому автоматические проверки не нашли нарушений.

    Уровень AAA не заявляется: автоматически его не проверить. Результат —
    «не хуже чем», так как автоматика покрывает лишь часть критериев.
    """
    failed = {
        r.rule.level
        for r in results
        if not r.rule.manual and r.violations > 0 and r.rule.level in ("A", "AA", "AAA")
    }
    if "A" in failed:
        return None
    if "AA" in failed:
        return "A"
    return "AA"
