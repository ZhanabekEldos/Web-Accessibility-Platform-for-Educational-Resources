import { useState } from "react";
import { api } from "../api.js";
import { BarList, Distribution, TrendChart } from "../components/Charts.jsx";
import { useToast } from "../components/Toast.jsx";
import { Button, EmptyState, ErrorNotice, Field, ImpactBadge, LinkButton, Loading, PageHead, Panel, ScoreMark } from "../components/ui.jsx";
import { formatNumber, scoreBand } from "../format.js";
import { useApi, usePageTitle } from "../hooks.js";
import { useI18n } from "../i18n/index.jsx";
import { Link, useQueryState } from "../router.jsx";

const PRINCIPLES = ["perceivable", "operable", "understandable", "robust"];

export default function Dashboard() {
  const { t, lang } = useI18n();
  const toast = useToast();
  usePageTitle(t("nav.dashboard"));
  const [query, setQuery] = useQueryState();
  const collectionId = query.get("collection") || "";
  const collections = useApi("/collections");
  const stats = useApi("/stats/overview", { collection_id: collectionId });
  const [seeding, setSeeding] = useState(false);
  const academy = useApi("/academy");
  const events = useApi("/events", { unread: 1, per_page: 1 });

  const seed = async () => {
    setSeeding(true);
    try { await api.post("/demo/seed"); toast(t("dashboard.demoLoaded")); collections.reload(); stats.reload(); }
    catch (e) { toast(e.message, { type: "error" }); }
    finally { setSeeding(false); }
  };

  const filter = collections.data?.items.length ? (
    <Field label={t("dashboard.scope")}>{(p) => (
      <select {...p} className="select" value={collectionId} onChange={(e) => setQuery({ collection: e.target.value })}>
        <option value="">{t("dashboard.allResources")}</option>
        {collections.data.items.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>)}</Field>
  ) : null;

  const head = <PageHead title={t("dashboard.title")} actions={filter}>{t("dashboard.lead")}</PageHead>;
  if (stats.loading && !stats.data) return <>{head}<Loading /></>;
  if (stats.error) return <>{head}<ErrorNotice error={stats.error} onRetry={stats.reload} /></>;

  const s = stats.data;
  const tot = s.totals;
  if (tot.resources === 0) {
    return (
      <>
        {head}
        <EmptyState title={t("dashboard.emptyTitle")} actions={<>
          <LinkButton to="/check" variant="primary" icon="check">{t("nav.check")}</LinkButton>
          <Button icon="sparkles" busy={seeding} onClick={seed}>{t("dashboard.loadDemo")}</Button>
        </>}>{t("dashboard.emptyText")}</EmptyState>
      </>
    );
  }

  const band = scoreBand(tot.avg_score);
  const improvement = s.improvement;
  return (
    <div className="stack-lg">
      {head}
      <section className="panel" aria-labelledby="hero-title">
        <div className="verdict">
          <ScoreMark score={tot.avg_score} size="lg" label={t("score.aria", { score: formatNumber(tot.avg_score, lang, 0), band: t(`band.${band}`) })} />
          <div className="verdict__text">
            <h2 id="hero-title">{t("dashboard.avgTitle")}</h2>
            <p className="muted">{t("dashboard.avgText", { n: tot.scanned, total: tot.resources })}</p>
            {improvement.avg_delta != null && improvement.tracked > 0 && (
              <p><strong className={improvement.avg_delta >= 0 ? "delta delta--up" : "delta delta--down"}>{improvement.avg_delta > 0 ? "▲ +" : improvement.avg_delta < 0 ? "▼ " : ""}{formatNumber(improvement.avg_delta, lang)}</strong> {t("dashboard.improvement", { n: improvement.tracked })}</p>
            )}
            <Distribution label={t("dashboard.bands")} items={[
              { key: "good", label: t("band.good"), value: tot.good, cls: "good" },
              { key: "fair", label: t("band.fair"), value: tot.fair, cls: "fair" },
              { key: "poor", label: t("band.poor"), value: tot.poor, cls: "poor" },
              { key: "none", label: t("band.none"), value: tot.unscanned, cls: "none" },
            ]} />
          </div>
        </div>
      </section>

      <div className="grid grid--2">
        <Panel title={t("dashboard.trend")}><TrendChart data={s.trend} /></Panel>
        <Panel title={t("dashboard.principles")}>
          <BarList items={PRINCIPLES.map((p) => ({ key: p, label: t(`principle.${p}`), value: s.by_principle[p], cls: s.by_principle[p] == null ? "" : scoreBand(s.by_principle[p]) }))} format={(v) => formatNumber(v, lang, 0)} />
          <p className="muted small" style={{ marginTop: "1rem" }}>{t("dashboard.principlesHint")}</p>
        </Panel>
      </div>

      <div className="grid grid--2">
        <Panel title={t("dashboard.levels")}>
          <Distribution label={t("dashboard.levels")} items={[
            { key: "aa", label: "WCAG AA", value: tot.level_aa, cls: "good" },
            { key: "a", label: "WCAG A", value: tot.level_a, cls: "fair" },
            { key: "none", label: t("level.none"), value: tot.level_none, cls: "poor" },
          ]} />
          <h3 style={{ margin: "1.5rem 0 0.75rem" }}>{t("dashboard.openIssues")}</h3>
          <Distribution label={t("dashboard.openIssues")} items={["critical", "serious", "moderate", "minor"].map((i) => ({ key: i, label: t(`impact.${i}`), value: s.by_impact[i], cls: i }))} />
        </Panel>
        <Panel title={t("dashboard.topRules")} aside={<Link to="/rules">{t("dashboard.allRules")}</Link>}>
          {s.top_rules.length === 0 ? <p className="muted">{t("dashboard.noIssues")}</p> : (
            <ul className="plain-list">
              {s.top_rules.map((r) => (
                <li key={r.rule_id}>
                  <span><ImpactBadge impact={r.impact} /> <Link to={`/rules?q=${r.rule_id}`}>{r.rule_id}</Link></span>
                  <span className="muted small nowrap">{t("dashboard.ruleResources", { n: r.resources })}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <Panel title={t("dashboard.next")}>
        <div className="grid grid--2">
          <div className="stack" style={{ gap: "0.4rem" }}>
            <h3>{t("dashboard.academy")}</h3>
            <p className="muted">{academy.data ? t("dashboard.academyText", { done: academy.data.completed, total: academy.data.total }) : "…"}</p>
            <div><LinkButton to="/academy" size="sm">{t("dashboard.academyGo")}</LinkButton></div>
          </div>
          <div className="stack" style={{ gap: "0.4rem" }}>
            <h3>{t("dashboard.events")}</h3>
            <p className="muted">{events.data ? (events.data.unread ? t("dashboard.eventsText", { n: events.data.unread }) : t("dashboard.eventsNone")) : "…"}</p>
            <div><LinkButton to="/notifications" size="sm">{t("dashboard.eventsGo")}</LinkButton></div>
          </div>
        </div>
      </Panel>

      {s.worst.length > 0 && (
        <Panel title={t("dashboard.worst")} aside={<Link to="/resources?sort=score&order=asc">{t("dashboard.allResources")}</Link>}>
          <ul className="plain-list">
            {s.worst.map((r) => (
              <li key={r.id}>
                <Link to={`/resources/${r.id}`} className="rowlink"><strong>{r.title}</strong></Link>
                <span className="row" style={{ gap: "1rem" }}><span className="muted small">{t("resources.violationsN", { n: r.violations })}</span><ScoreMark score={r.last_score} size="sm" /></span>
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  );
}
