"""Рекомендации: что исправить в первую очередь и насколько вырастет оценка."""
from __future__ import annotations

from typing import Any

from ..a11y.i18n import rule_texts
from ..a11y.registry import REGISTRY
from ..a11y.scoring import RuleResult, weighted_score


def build(summary: dict[str, Any], current_score: float | None, lang: str, limit: int = 12) -> list[dict[str, Any]]:
    """Приоритетный план исправлений по сводке проверки.

    Для каждого правила с нарушениями считается, на сколько баллов вырастет общая оценка,
    если исправить его полностью. Список упорядочен по приросту, затем по серьёзности.
    """
    stats: dict[str, list[int]] = summary.get("rule_stats", {})
    results: list[RuleResult] = []
    for rule_id, (applicable, violations, reviews) in stats.items():
        rule = REGISTRY.get(rule_id)
        if rule:
            results.append(RuleResult(rule, applicable, violations, reviews))
    base = current_score if current_score is not None else weighted_score(results) or 100.0
    plan: list[dict[str, Any]] = []
    for r in results:
        if r.violations == 0 or r.rule.manual:
            continue
        fixed = [RuleResult(x.rule, x.applicable, 0 if x.rule.id == r.rule.id else x.violations, x.reviews) for x in results]
        gain = round((weighted_score(fixed) or 100.0) - base, 1)
        texts = rule_texts(r.rule.id, lang)
        plan.append(
            {
                "rule_id": r.rule.id,
                "title": texts.get("title", r.rule.id),
                "fix": texts.get("fix", ""),
                "impact": r.rule.impact,
                "level": r.rule.level,
                "wcag": list(r.rule.wcag),
                "violations": r.violations,
                "gain": max(gain, 0.0),
            }
        )
    order = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}
    plan.sort(key=lambda p: (-p["gain"], order[p["impact"]], -p["violations"]))
    return plan[:limit]
