"""Реестр правил и инфраструктура для их описания.

Правило — обычная функция ``check(doc, report)``, зарегистрированная декоратором
``@rule``. Чтобы добавить проверку, достаточно создать функцию в любом модуле
пакета ``app.a11y.rules`` и добавить тексты в ``locales/*.json`` (тест
``test_locales`` подскажет, если что-то забыто).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Iterable, Iterator

from .wcag import CATALOG

if TYPE_CHECKING:  # pragma: no cover
    from bs4 import Tag

    from .document import Document

IMPACTS = ("critical", "serious", "moderate", "minor")
IMPACT_WEIGHT = {"critical": 10, "serious": 7, "moderate": 3, "minor": 1}
PRINCIPLES = ("perceivable", "operable", "understandable", "robust")
# BP — «лучшие практики»: не привязаны к критерию WCAG и не влияют на уровень соответствия.
LEVELS = ("A", "AA", "AAA", "BP")

_WS = re.compile(r"\s+")


@dataclass(slots=True)
class Finding:
    rule_id: str
    selector: str
    snippet: str
    line: int | None
    needs_review: bool = False
    data: dict[str, Any] = field(default_factory=dict)
    identity: str = ""
    occurrence: int = 1

    @property
    def fingerprint(self) -> str:
        """Устойчивый идентификатор замечания между сканированиями.

        Строится из правила и «личности» элемента (тег, id, name, src, href, начало текста),
        а не из CSS-пути и не из всего фрагмента: так замечание узнаётся и после правки
        соседних атрибутов или перестановки блоков, а статусы (триаж) переносятся на новый скан.
        Одинаковые элементы различаются порядковым номером.
        """
        raw = f"{self.rule_id}|{self.identity or self.selector}|{self.occurrence}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


class RuleReport:
    """Собирает результаты одного запуска правила."""

    __slots__ = ("rule_id", "doc", "limit", "applicable", "findings", "dropped_violations", "dropped_reviews", "_seen")

    def __init__(self, rule_id: str, doc: "Document", limit: int) -> None:
        self.rule_id = rule_id
        self.doc = doc
        self.limit = limit
        self.applicable = 0
        self.findings: list[Finding] = []
        # Замечания сверх лимита в список не попадают, но в счётчиках учитываются.
        self.dropped_violations = 0
        self.dropped_reviews = 0
        self._seen: dict[str, int] = {}

    def checked(self, n: int = 1) -> None:
        """Отметить, что правило применимо к ``n`` элементам (даже если всё в порядке)."""
        self.applicable += n

    def fail(self, el: "Tag", *, data: dict[str, Any] | None = None, review: bool = False) -> None:
        """Зафиксировать замечание. ``review=True`` — требуется ручная проверка."""
        if len(self.findings) >= self.limit:
            if review:
                self.dropped_reviews += 1
            else:
                self.dropped_violations += 1
            return
        identity = self.doc.identity(el)
        self._seen[identity] = self._seen.get(identity, 0) + 1
        self.findings.append(
            Finding(
                rule_id=self.rule_id,
                selector=self.doc.selector(el),
                snippet=self.doc.snippet(el),
                line=getattr(el, "sourceline", None),
                needs_review=review,
                data=data or {},
                identity=identity,
                occurrence=self._seen[identity],
            )
        )

    def review(self, el: "Tag", *, data: dict[str, Any] | None = None) -> None:
        self.fail(el, data=data, review=True)

    @property
    def violations(self) -> int:
        return sum(1 for f in self.findings if not f.needs_review) + self.dropped_violations

    @property
    def reviews(self) -> int:
        return sum(1 for f in self.findings if f.needs_review) + self.dropped_reviews

    @property
    def dropped(self) -> int:
        return self.dropped_violations + self.dropped_reviews


CheckFn = Callable[["Document", RuleReport], None]


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    check: CheckFn
    wcag: tuple[str, ...]
    level: str
    impact: str
    principle: str
    tags: tuple[str, ...] = ()
    manual: bool = False  # результаты — только «проверить вручную», в оценку не входят
    bad: str = ""
    good: str = ""

    @property
    def weight(self) -> int:
        return IMPACT_WEIGHT[self.impact]


class RuleRegistry:
    def __init__(self) -> None:
        self._rules: dict[str, Rule] = {}

    def register(self, rule: Rule) -> None:
        if rule.id in self._rules:
            raise ValueError(f"Правило {rule.id!r} уже зарегистрировано")
        if rule.impact not in IMPACTS:
            raise ValueError(f"{rule.id}: неизвестная серьёзность {rule.impact!r}")
        if rule.principle not in PRINCIPLES:
            raise ValueError(f"{rule.id}: неизвестный принцип {rule.principle!r}")
        if rule.level not in LEVELS:
            raise ValueError(f"{rule.id}: неизвестный уровень {rule.level!r}")
        for sc in rule.wcag:
            if sc not in CATALOG:
                raise ValueError(f"{rule.id}: критерий {sc} отсутствует в wcag.CATALOG")
        self._rules[rule.id] = rule

    def get(self, rule_id: str) -> Rule | None:
        return self._rules.get(rule_id)

    def __iter__(self) -> Iterator[Rule]:
        return iter(self._rules.values())

    def __len__(self) -> int:
        return len(self._rules)

    def __contains__(self, rule_id: object) -> bool:
        return rule_id in self._rules

    def select(self, *, ids: Iterable[str] | None = None, tags: Iterable[str] | None = None) -> list[Rule]:
        rules = list(self._rules.values())
        if ids is not None:
            wanted = set(ids)
            rules = [r for r in rules if r.id in wanted]
        if tags is not None:
            wanted_tags = set(tags)
            rules = [r for r in rules if wanted_tags & set(r.tags)]
        return rules


REGISTRY = RuleRegistry()


def rule(
    *,
    id: str,
    level: str,
    impact: str,
    principle: str,
    wcag: Iterable[str] = (),
    tags: Iterable[str] = (),
    manual: bool = False,
    bad: str = "",
    good: str = "",
) -> Callable[[CheckFn], CheckFn]:
    """Декоратор регистрации правила."""

    def decorator(fn: CheckFn) -> CheckFn:
        REGISTRY.register(
            Rule(
                id=id,
                check=fn,
                wcag=tuple(wcag),
                level=level,
                impact=impact,
                principle=principle,
                tags=tuple(tags),
                manual=manual,
                bad=bad,
                good=good,
            )
        )
        return fn

    return decorator
