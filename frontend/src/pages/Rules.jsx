import { useMemo, useState } from "react";
import { Field, ImpactBadge, Loading, ErrorNotice, PageHead } from "../components/ui.jsx";
import { useApi, usePageTitle } from "../hooks.js";
import { useI18n } from "../i18n/index.jsx";
import { useQueryState } from "../router.jsx";

export default function Rules() {
  const { t } = useI18n();
  usePageTitle(t("nav.rules"));
  const { data, error, loading, reload } = useApi("/rules");
  const [query, setQuery] = useQueryState();
  const q = query.get("q") || "";
  const [principle, setPrinciple] = useState("");
  const [impact, setImpact] = useState("");
  const [level, setLevel] = useState("");

  const items = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return (data?.items || []).filter((r) =>
      (!principle || r.principle === principle) && (!impact || r.impact === impact) && (!level || r.level === level) &&
      (!needle || `${r.id} ${r.title} ${r.description} ${r.wcag.map((c) => c.id).join(" ")} ${r.tags.join(" ")}`.toLowerCase().includes(needle)));
  }, [data, q, principle, impact, level]);

  return (
    <div className="stack-lg">
      <PageHead title={t("rules.title")}>{t("rules.lead", { n: data?.total ?? "…" })}</PageHead>
      <div className="filters" role="search" aria-label={t("findings.filters")}>
        <Field label={t("findings.search")} className="field--search">{(p) => <input {...p} className="input" type="search" value={q} onChange={(e) => setQuery({ q: e.target.value })} />}</Field>
        <Field label={t("rules.principle")}>{(p) => (
          <select {...p} className="select" value={principle} onChange={(e) => setPrinciple(e.target.value)}>
            <option value="">{t("common.any")}</option>
            {["perceivable", "operable", "understandable", "robust"].map((x) => <option key={x} value={x}>{t(`principle.${x}`)}</option>)}
          </select>)}</Field>
        <Field label={t("findings.impact")}>{(p) => (
          <select {...p} className="select" value={impact} onChange={(e) => setImpact(e.target.value)}>
            <option value="">{t("common.any")}</option>
            {["critical", "serious", "moderate", "minor"].map((x) => <option key={x} value={x}>{t(`impact.${x}`)}</option>)}
          </select>)}</Field>
        <Field label={t("rules.level")}>{(p) => (
          <select {...p} className="select" value={level} onChange={(e) => setLevel(e.target.value)}>
            <option value="">{t("common.any")}</option>
            {["A", "AA", "BP"].map((x) => <option key={x} value={x}>{x === "BP" ? t("findings.bestPractice") : `WCAG ${x}`}</option>)}
          </select>)}</Field>
      </div>
      {error ? <ErrorNotice error={error} onRetry={reload} /> : loading && !data ? <Loading /> : (
        <>
          <p className="muted small" role="status">{t("rules.shown", { n: items.length })}</p>
          <div className="stack">
            {items.map((r) => (
              <details key={r.id} className={`rule-group rule-group--${r.impact}`}>
                <summary>
                  <span className="rule-group__title">{r.title}</span>
                  <span className="rule-group__count"><Chevron /></span>
                  <span className="rule-group__meta">
                    <ImpactBadge impact={r.impact} />
                    <span className="chip">{r.level === "BP" ? t("findings.bestPractice") : `WCAG ${r.level}`}</span>
                    <span className="chip">{t(`principle.${r.principle}`)}</span>
                    {r.manual && <span className="badge badge--neutral">{t("findings.manual")}</span>}
                    {r.wcag.map((c) => <span className="chip" key={c.id}>{c.id}</span>)}
                  </span>
                </summary>
                <div className="rule-group__body">
                  <p>{r.description}</p>
                  <div className="howto"><strong>{t("findings.howToFix")}</strong>{r.fix}</div>
                  <div className="example">
                    <figure className="bad" style={{ margin: 0 }}><figcaption>✕ {t("rules.bad")}</figcaption><pre className="code"><code>{r.bad}</code></pre></figure>
                    <figure className="good" style={{ margin: 0 }}><figcaption>✓ {t("rules.good")}</figcaption><pre className="code"><code>{r.good}</code></pre></figure>
                  </div>
                  <div className="row small" style={{ gap: "0.5rem" }}>
                    <code>{r.id}</code>
                    {r.wcag.map((c) => <a key={c.id} href={c.url} target="_blank" rel="noreferrer noopener">{c.id} {c.name} <span className="sr-only">({t("common.newTab")})</span></a>)}
                  </div>
                </div>
              </details>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function Chevron() {
  return <svg className="rule-group__chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m9 6 6 6-6 6" /></svg>;
}
