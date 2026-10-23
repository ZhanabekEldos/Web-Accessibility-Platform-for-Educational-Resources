import { useMemo, useState } from "react";
import { api } from "../api.js";
import { formatDate, formatNumber, scoreBand } from "../format.js";
import { useI18n } from "../i18n/index.jsx";
import { BarList, Distribution } from "./Charts.jsx";
import { Icon } from "./icons.jsx";
import { useToast } from "./Toast.jsx";
import { BandBadge, Button, Field, ImpactBadge, LevelBadge, ScoreMark, Stat } from "./ui.jsx";

const IMPACTS = ["critical", "serious", "moderate", "minor"];
const PRINCIPLES = ["perceivable", "operable", "understandable", "robust"];
const STATUSES = ["open", "in_progress", "fixed", "wontfix", "false_positive"];
const DONE = new Set(["fixed", "wontfix", "false_positive"]);

/** Крупная сводка: отметка, уровень, счётчики, динамика, оценки по принципам WCAG. */
export function ScanVerdict({ scan }) {
  const { t, lang } = useI18n();
  const band = scoreBand(scan.score);
  const delta = scan.previous ? Math.round((scan.score - scan.previous.score) * 10) / 10 : null;
  const rules = scan.summary.rules;
  const impacts = IMPACTS.map((i) => ({ key: i, label: t(`impact.${i}`), value: scan.summary.by_impact[i], cls: i }));
  const principleBars = PRINCIPLES.map((p) => ({
    key: p, label: t(`principle.${p}`), value: scan.summary.principles?.[p] ?? null,
    cls: scan.summary.principles?.[p] == null ? "" : scoreBand(scan.summary.principles[p]),
  }));
  return (
    <section className="panel stack-lg" aria-labelledby="verdict-title">
      <div className="verdict">
        <ScoreMark score={scan.score} size="lg" />
        <div className="verdict__text">
          <h2 id="verdict-title">{t(`verdict.${band}`)}</h2>
          <div className="row">
            <BandBadge score={scan.score} />
            <LevelBadge level={scan.level} />
            {delta != null && delta !== 0 && (
              <span className={`delta ${delta > 0 ? "delta--up" : "delta--down"}`}>
                {delta > 0 ? "▲ +" : "▼ "}{formatNumber(delta, lang)} {t("report.sinceLast", { date: formatDate(scan.previous.created_at, lang) })}
              </span>
            )}
          </div>
          <p className="muted">{t(scan.level ? `report.level.${scan.level}` : "report.level.none")}</p>
          <dl className="stats">
            <Stat label={t("report.violations")} value={scan.violations} cls="num" />
            <Stat label={t("report.reviews")} value={scan.reviews} cls="num" />
            <Stat label={t("report.rulesPassed")} value={rules.passed} cls="num" />
            <Stat label={t("report.rulesFailed")} value={rules.failed} cls="num" />
          </dl>
        </div>
      </div>
      <div className="grid grid--2">
        <div><h3 style={{ marginBottom: "0.75rem" }}>{t("report.byPrinciple")}</h3><BarList items={principleBars} format={(v) => formatNumber(v, lang, 0)} /></div>
        <div><h3 style={{ marginBottom: "0.75rem" }}>{t("report.byImpact")}</h3><Distribution items={impacts} label={t("report.byImpact")} /></div>
      </div>
      <p className="muted small">{t("report.disclaimer")}</p>
    </section>
  );
}

/** Замечания, сгруппированные по правилам, с фильтрами и статусами работы (триаж). */
export function FindingsView({ scan, resourceId, focusRule, onClearFocus }) {
  const { t, lang } = useI18n();
  const toast = useToast();
  const [impact, setImpact] = useState("");
  const [kind, setKind] = useState("violations");
  const [status, setStatus] = useState("");
  const [query, setQuery] = useState("");
  const [overrides, setOverrides] = useState({});
  const [expanded, setExpanded] = useState({});

  const stateOf = (f) => overrides[f.fingerprint] || f.triage;

  const groups = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return scan.groups
      .map((g) => {
        if (focusRule && g.rule_id !== focusRule) return null;
        if (impact && g.impact !== impact) return null;
        const findings = g.findings.filter((f) => {
          if (kind === "violations" && f.needs_review) return false;
          if (kind === "review" && !f.needs_review) return false;
          const st = (overrides[f.fingerprint] || f.triage).status;
          if (status === "active" && DONE.has(st)) return false;
          if (status && status !== "active" && st !== status) return false;
          if (needle && !`${f.message} ${f.selector} ${f.snippet} ${g.title}`.toLowerCase().includes(needle)) return false;
          return true;
        });
        return findings.length ? { ...g, findings } : null;
      })
      .filter(Boolean);
  }, [scan, impact, kind, status, query, overrides, focusRule]);

  const save = async (finding, patch) => {
    const current = stateOf(finding);
    const next = { ...current, ...patch };
    setOverrides((o) => ({ ...o, [finding.fingerprint]: next }));
    try {
      await api.put(`/resources/${resourceId}/triage/${finding.fingerprint}`, { status: next.status, note: next.note || "" });
    } catch (e) {
      setOverrides((o) => ({ ...o, [finding.fingerprint]: current }));
      toast(e.message, { type: "error" });
    }
  };

  const truncated = Object.keys(scan.truncated || {}).length > 0;

  return (
    <div className="stack">
      {focusRule && (
        <div className="notice notice--info">
          <span className="grow">{t("findings.focused", { rule: scan.groups.find((g) => g.rule_id === focusRule)?.title || focusRule })}</span>
          <Button size="sm" onClick={onClearFocus}>{t("findings.showAll")}</Button>
        </div>
      )}
      <div className="filters" role="search" aria-label={t("findings.filters")}>
        <Field label={t("findings.search")} className="field--search">{(p) => <input {...p} className="input" type="search" value={query} onChange={(e) => setQuery(e.target.value)} />}</Field>
        <Field label={t("findings.kind")}>{(p) => (
          <select {...p} className="select" value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="violations">{t("findings.kindViolations")}</option>
            <option value="review">{t("findings.kindReview")}</option>
            <option value="all">{t("findings.kindAll")}</option>
          </select>)}</Field>
        <Field label={t("findings.impact")}>{(p) => (
          <select {...p} className="select" value={impact} onChange={(e) => setImpact(e.target.value)}>
            <option value="">{t("common.any")}</option>
            {IMPACTS.map((i) => <option key={i} value={i}>{t(`impact.${i}`)}</option>)}
          </select>)}</Field>
        {resourceId && <Field label={t("findings.status")}>{(p) => (
          <select {...p} className="select" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">{t("common.any")}</option>
            <option value="active">{t("findings.statusActive")}</option>
            {STATUSES.map((s) => <option key={s} value={s}>{t(`triage.${s}`)}</option>)}
          </select>)}</Field>}
      </div>

      {truncated && <div className="notice">{t("findings.truncated")}</div>}
      <p className="muted small" role="status">{t("findings.shown", { n: groups.reduce((n, g) => n + g.findings.length, 0) })}</p>

      {groups.length === 0 && (
        <div className="notice notice--ok">{scan.violations === 0 && scan.reviews === 0 ? t("findings.none") : t("findings.noMatch")}</div>
      )}

      {groups.map((g, gi) => {
        const limit = expanded[g.rule_id] ? Infinity : 15;
        return (
          <details key={g.rule_id} className={`rule-group rule-group--${g.impact}`} open={focusRule === g.rule_id || (g.impact === "critical" && gi < 3 && !g.manual) || undefined}>
            <summary>
              <span className="rule-group__title">{g.title}</span>
              <span className="rule-group__count"><span className="num">{g.findings.length}</span><Icon name="chevron" className="rule-group__chev" /></span>
              <span className="rule-group__meta">
                <ImpactBadge impact={g.impact} />
                {g.manual && <span className="badge badge--neutral">{t("findings.manual")}</span>}
                <span className="chip" title={t("findings.levelHint")}>{g.level === "BP" ? t("findings.bestPractice") : `WCAG ${g.level}`}</span>
                {g.wcag.map((c) => <a key={c.id} className="chip" href={c.url} target="_blank" rel="noreferrer noopener" onClick={(e) => e.stopPropagation()} aria-label={`${t("findings.criterion")} ${c.id} ${c.name} (${t("common.newTab")})`}>{c.id}</a>)}
              </span>
            </summary>
            <div className="rule-group__body">
              <div className="howto"><strong>{t("findings.howToFix")}</strong>{g.fix}</div>
              <ul className="stack" style={{ listStyle: "none" }}>
                {g.findings.slice(0, limit).map((f) => {
                  const st = stateOf(f);
                  return (
                    <li key={f.id} className={`finding ${DONE.has(st.status) ? "finding--done" : ""}`}>
                      <div className="finding__msg">{f.message}{f.needs_review && <> <span className="badge badge--neutral">{t("findings.review")}</span></>}</div>
                      <div className="finding__where"><code>{f.selector}</code>{f.line ? <span>{t("findings.line", { n: f.line })}</span> : null}</div>
                      <pre className="code"><code>{f.snippet}</code></pre>
                      {resourceId && (
                        <div className="finding__actions">
                          <Field label={t("findings.status")}>{(p) => (
                            <select {...p} className="select" value={st.status} onChange={(e) => save(f, { status: e.target.value })}>
                              {STATUSES.map((s) => <option key={s} value={s}>{t(`triage.${s}`)}</option>)}
                            </select>)}</Field>
                          <Field label={t("findings.note")} className="grow">{(p) => (
                            <input {...p} className="input" maxLength={500} defaultValue={st.note} onBlur={(e) => { if (e.target.value !== (st.note || "")) save(f, { note: e.target.value }); }} />)}</Field>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
              {g.findings.length > limit && <Button size="sm" onClick={() => setExpanded((x) => ({ ...x, [g.rule_id]: true }))}>{t("findings.showMore", { n: g.findings.length - limit })}</Button>}
            </div>
          </details>
        );
      })}
    </div>
  );
}

/** Приоритетный план: сначала то, что сильнее всего поднимет оценку. */
export function PlanView({ scan, onShowRule }) {
  const { t, lang } = useI18n();
  const plan = scan.plan.filter((p) => p.gain > 0 || p.violations > 0);
  if (!plan.length) return <div className="notice notice--ok">{t("plan.done")}</div>;
  return (
    <div className="stack">
      <p className="muted">{t("plan.intro")}</p>
      <ol className="plan">
        {plan.map((p) => (
          <li key={p.rule_id}>
            <div className="stack" style={{ gap: "0.4rem" }}>
              <h3>{p.title}</h3>
              <div className="row" style={{ gap: "0.4rem" }}>
                <ImpactBadge impact={p.impact} />
                <span className="chip">{t("plan.count", { n: p.violations })}</span>
                {p.wcag.map((c) => <span key={c} className="chip">{c}</span>)}
              </div>
              <p>{p.fix}</p>
              {onShowRule && <div><Button size="sm" onClick={() => onShowRule(p.rule_id)}>{t("plan.show")}</Button></div>}
            </div>
            <div className="plan__gain" title={t("plan.gainHint")}>+{formatNumber(p.gain, lang)}<div className="small muted" style={{ fontFamily: "var(--sans)", fontWeight: 400 }}>{t("plan.points", { n: Math.round(p.gain) })}</div></div>
          </li>
        ))}
      </ol>
    </div>
  );
}

/** Сравнение двух проверок: что исправлено, что появилось, что осталось. */
export function DiffView({ diff }) {
  const { t, lang } = useI18n();
  const delta = diff.score_delta;
  return (
    <div className="stack">
      <div className="panel">
        <div className="row" style={{ gap: "1.5rem" }}>
          <div><div className="small muted">{formatDate(diff.base.created_at, lang, true)}</div><ScoreMark score={diff.base.score} size="md" /></div>
          <span aria-hidden="true" style={{ fontSize: "1.8rem" }}>→</span>
          <div><div className="small muted">{formatDate(diff.scan.created_at, lang, true)}</div><ScoreMark score={diff.scan.score} size="md" /></div>
          <div className={`delta ${delta >= 0 ? "delta--up" : "delta--down"}`} style={{ fontSize: "1.3rem" }}>{delta > 0 ? "+" : ""}{formatNumber(delta, lang)}</div>
        </div>
        <dl className="stats stats--spaced">
          <Stat label={t("diff.fixed")} value={diff.counts.fixed} cls="delta--up" />
          <Stat label={t("diff.new")} value={diff.counts.new} cls="delta--down" />
          <Stat label={t("diff.persisting")} value={diff.counts.persisting} cls="" />
        </dl>
      </div>
      <div className="diff-cols">
        <DiffList title={t("diff.fixedList")} items={diff.fixed} empty={t("diff.noneFixed")} />
        <DiffList title={t("diff.newList")} items={diff.new} empty={t("diff.noneNew")} />
      </div>
    </div>
  );
}

function DiffList({ title, items, empty }) {
  return (
    <section className="stack">
      <h3>{title}</h3>
      {items.length === 0 ? <p className="muted">{empty}</p> : (
        <ul className="diff-list">
          {items.map((f) => <li key={f.fingerprint}><ImpactBadge impact={f.impact} /> <strong>{f.title}</strong><div className="small muted">{f.message}</div></li>)}
        </ul>
      )}
    </section>
  );
}
