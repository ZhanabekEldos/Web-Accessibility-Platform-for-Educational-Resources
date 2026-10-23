"""Точка входа движка: ``analyze(html)`` → результат со списком замечаний и оценкой."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Iterable

from . import rules as _rules  # noqa: F401  (регистрация правил)
from .document import Document
from .registry import IMPACTS, LEVELS, PRINCIPLES, REGISTRY, Finding, Rule, RuleReport
from .scoring import RuleResult, conformance_level, principle_scores, weighted_score

log = logging.getLogger(__name__)

ENGINE_VERSION = "1.0.0"
DEFAULT_MAX_FINDINGS_PER_RULE = 150


class EmptyDocumentError(ValueError):
    """Передан пустой документ."""


@dataclass(slots=True)
class AnalysisResult:
    score: float
    level: str | None
    page_title: str
    lang: str | None
    findings: list[Finding]
    summary: dict[str, Any]
    duration_ms: int
    engine_version: str = ENGINE_VERSION
    html_bytes: int = 0
    extras: dict[str, Any] = field(default_factory=dict)


def analyze(
    html: str,
    *,
    rules: Iterable[Rule] | None = None,
    max_findings_per_rule: int = DEFAULT_MAX_FINDINGS_PER_RULE,
) -> AnalysisResult:
    if not html or not html.strip():
        raise EmptyDocumentError("Документ пуст")
    started = time.perf_counter()
    doc = Document(html)

    results: list[RuleResult] = []
    findings: list[Finding] = []
    errors: list[str] = []
    truncated: dict[str, int] = {}

    for rule in rules if rules is not None else REGISTRY:
        report = RuleReport(rule.id, doc, max_findings_per_rule)
        try:
            rule.check(doc, report)
        except Exception:  # noqa: BLE001 — сбой одного правила не должен ронять весь анализ
            log.exception("Правило %s завершилось с ошибкой", rule.id)
            errors.append(rule.id)
            continue
        results.append(RuleResult(rule, report.applicable, report.violations, report.reviews))
        findings.extend(report.findings)
        if report.dropped:
            truncated[rule.id] = report.dropped

    findings.sort(key=lambda f: (_impact_rank(f.rule_id), f.needs_review, f.rule_id, f.line or 0))

    summary = _build_summary(results, errors, truncated)
    score = weighted_score(results)
    return AnalysisResult(
        score=100.0 if score is None else score,
        level=conformance_level(results),
        page_title=doc.title[:300],
        lang=doc.lang,
        findings=findings,
        summary=summary,
        duration_ms=int((time.perf_counter() - started) * 1000),
        html_bytes=len(html.encode("utf-8", errors="ignore")),
    )


def _impact_rank(rule_id: str) -> int:
    rule = REGISTRY.get(rule_id)
    return IMPACTS.index(rule.impact) if rule else len(IMPACTS)


def _build_summary(results: list[RuleResult], errors: list[str], truncated: dict[str, int]) -> dict[str, Any]:
    by_impact = {i: 0 for i in IMPACTS}
    by_principle = {p: 0 for p in PRINCIPLES}
    by_level = {lvl: 0 for lvl in LEVELS}
    violations = reviews = 0
    passed = failed = review_only = not_applicable = 0
    rule_stats: dict[str, list[int]] = {}

    for r in results:
        if r.applicable == 0 and r.violations == 0 and r.reviews == 0:
            not_applicable += 1
            continue
        rule_stats[r.rule.id] = [r.applicable, r.violations, r.reviews]
        reviews += r.reviews
        if r.violations:
            failed += 1
            violations += r.violations
            by_impact[r.rule.impact] += r.violations
            by_principle[r.rule.principle] += r.violations
            by_level[r.rule.level] += r.violations
        elif r.reviews:
            review_only += 1
        else:
            passed += 1

    return {
        "violations": violations,
        "reviews": reviews,
        "by_impact": by_impact,
        "by_principle": by_principle,
        "by_level": by_level,
        "principles": principle_scores(results),
        "rules": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "review": review_only,
            "not_applicable": not_applicable,
            "errors": errors,
        },
        "rule_stats": rule_stats,
        "truncated": truncated,
    }
