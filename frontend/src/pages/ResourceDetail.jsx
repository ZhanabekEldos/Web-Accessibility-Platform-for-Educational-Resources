import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useConfirm } from "../components/Dialog.jsx";
import { Menu } from "../components/Menu.jsx";
import { AuditView } from "../components/AuditView.jsx";
import { StatementView } from "../components/StatementView.jsx";
import { ResourceForm } from "../components/ResourceForm.jsx";
import { DiffView, FindingsView, PlanView, ScanVerdict } from "../components/ScanReport.jsx";
import { TabPanel, Tabs } from "../components/Tabs.jsx";
import { useToast } from "../components/Toast.jsx";
import { Button, EmptyState, ErrorNotice, Loading, PageHead, Panel, ScoreMark } from "../components/ui.jsx";
import { formatDate } from "../format.js";
import { useApi, usePageTitle } from "../hooks.js";
import { useI18n } from "../i18n/index.jsx";
import { Link, useQueryState, useRouter } from "../router.jsx";

export default function ResourceDetail({ id }) {
  const { t, lang } = useI18n();
  const toast = useToast();
  const confirm = useConfirm();
  const { navigate } = useRouter();
  const [query, setQuery] = useQueryState();
  const scanParam = query.get("scan");
  const tab = query.get("tab") || "findings";
  const [focusRule, setFocusRule] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [compare, setCompare] = useState(null);

  const resource = useApi(`/resources/${id}`);
  const scanPath = scanParam ? `/scans/${scanParam}` : `/resources/${id}/latest`;
  const scan = useApi(scanPath, undefined, { skip: !resource.data || (!scanParam && !resource.data.last_scan_id) });
  const history = useApi(`/resources/${id}/scans`, { limit: 50 });
  const collections = useApi("/collections");
  const audit = useApi(`/resources/${id}/audit`);
  const [auditProgress, setAuditProgress] = useState(null);
  const auditNow = auditProgress || audit.data?.progress;
  const diff = useApi(compare ? `/scans/${compare}/diff` : "", undefined, { skip: !compare });
  usePageTitle(resource.data?.title);
  useEffect(() => { setCompare(null); setFocusRule(null); }, [id, scanParam]);
  useEffect(() => { setAuditProgress(null); }, [id]);

  if (resource.error) return <ErrorNotice error={resource.error} onRetry={resource.reload} />;
  if (!resource.data) return <Loading />;
  const r = resource.data;
  const current = scan.data;

  const refresh = () => { resource.reload(); scan.reload(); history.reload(); };
  const runScan = async () => {
    setScanning(true);
    try {
      const res = await api.post(`/resources/${id}/scan`);
      toast(t("resources.scanned", { title: r.title, score: Math.round(res.score) }));
      if (scanParam) setQuery({ scan: "" }); else refresh();
      resource.reload(); history.reload();
    } catch (e) { toast(e.message, { type: "error" }); history.reload(); } finally { setScanning(false); }
  };
  const remove = async () => {
    if (!(await confirm({ title: t("resources.deleteTitle"), body: t("resources.deleteBody", { title: r.title }), confirmLabel: t("common.delete"), danger: true }))) return;
    try { await api.del(`/resources/${id}`); toast(t("resources.deleted")); navigate("/resources"); } catch (e) { toast(e.message, { type: "error" }); }
  };
  const changeSchedule = async (e) => {
    try { await api.patch(`/resources/${id}`, { schedule: e.target.value }); resource.reload(); toast(t("schedule.saved")); }
    catch (err) { toast(err.message, { type: "error" }); }
  };
  const setTab = (next) => setQuery({ tab: next === "findings" ? "" : next });
  const okScans = (history.data?.items || []).filter((s) => s.status === "ok");
  const viewingOld = scanParam && current && resource.data.last_scan_id !== current.id;

  const exportLinks = current && (
    <Menu label={t("detail.export")} icon="download">
      {["html", "csv", "json"].map((f) => <a key={f} href={api.exportUrl(current.id, f)} download>{t(`detail.export.${f}`)}</a>)}
    </Menu>
  );

  return (
    <div className="stack-lg">
      <PageHead
        title={r.title}
        crumbs={<nav className="crumbs" aria-label={t("common.breadcrumbs")}><Link to="/resources">{t("nav.resources")}</Link>{r.collection_name && <> / <Link to={`/resources?collection=${r.collection_id}`}>{r.collection_name}</Link></>}</nav>}
        actions={<>
          <Button variant="primary" icon="refresh" busy={scanning} onClick={runScan}>{t("detail.rescan")}</Button>
          {exportLinks}
          <Button icon="edit" onClick={() => setFormOpen(true)}>{t("common.edit")}</Button>
          <Button variant="danger" icon="trash" onClick={remove}>{t("common.delete")}</Button>
        </>}
      >
        {r.url ? <a href={r.url} target="_blank" rel="noreferrer noopener">{r.url}<span className="sr-only"> ({t("common.newTab")})</span></a> : t("detail.pastedHtml")}
        {" · "}{t(`kind.${r.kind}`)}
      </PageHead>

      {r.last_status === "error" && !current && <ErrorNotice error={{ message: t("detail.lastFailed") }} onRetry={runScan} />}

      {!r.last_scan_id && !scanParam ? (
        <EmptyState title={t("detail.notScanned")} actions={<Button variant="primary" icon="check" busy={scanning} onClick={runScan}>{t("detail.scanNow")}</Button>}>{t("detail.notScannedText")}</EmptyState>
      ) : scan.error ? <ErrorNotice error={scan.error} onRetry={scan.reload} />
        : !current ? <Loading />
        : (
          <>
            {viewingOld && (
              <div className="notice notice--info" role="status">
                <span className="grow">{t("detail.viewingOld", { date: formatDate(current.created_at, lang, true) })}</span>
                <Button size="sm" onClick={() => setQuery({ scan: "" })}>{t("detail.toLatest")}</Button>
              </div>
            )}
            <ScanVerdict scan={current} />
            <Panel>
              <Tabs id="res" label={t("report.sections")} value={tab} onChange={setTab} tabs={[
                { id: "findings", label: t("tab.findings"), count: current.violations + current.reviews },
                { id: "plan", label: t("tab.plan") },
                { id: "audit", label: t("tab.audit"), count: auditNow ? `${auditNow.done}/${auditNow.total}` : undefined },
                { id: "statement", label: t("tab.statement") },
                { id: "history", label: t("tab.history"), count: okScans.length || undefined },
                { id: "info", label: t("tab.info") },
              ]} />
              <TabPanel id="res" tab="findings" value={tab}>
                <FindingsView key={current.id} scan={current} resourceId={r.id} focusRule={focusRule} onClearFocus={() => setFocusRule(null)} />
              </TabPanel>
              <TabPanel id="res" tab="plan" value={tab}>
                <PlanView scan={current} onShowRule={(rule) => { setFocusRule(rule); setTab("findings"); }} />
              </TabPanel>
              <TabPanel id="res" tab="audit" value={tab}>
                <AuditView resourceId={r.id} onProgress={setAuditProgress} />
              </TabPanel>
              <TabPanel id="res" tab="statement" value={tab}>
                <StatementView resource={r} />
              </TabPanel>
              <TabPanel id="res" tab="history" value={tab}>
                <div className="stack-lg">
                  {history.loading && !history.data ? <Loading /> : (
                    <div className="table-wrap"><table className="table">
                      <caption className="sr-only">{t("tab.history")}</caption>
                      <thead><tr><th scope="col">{t("history.date")}</th><th scope="col">{t("resources.colScore")}</th><th scope="col">{t("resources.colIssues")}</th><th scope="col"><span className="sr-only">{t("common.actions")}</span></th></tr></thead>
                      <tbody>
                        {history.data.items.map((s) => (
                          <tr key={s.id}>
                            <th scope="row" style={{ fontWeight: 500 }}>{formatDate(s.created_at, lang, true)}</th>
                            <td>{s.status === "ok" ? <ScoreMark score={s.score} size="sm" /> : <span className="badge badge--poor">{t("history.error")}</span>}</td>
                            <td className="num">{s.status === "ok" ? <>{s.violations}{s.reviews > 0 && <span className="small muted"> · {t("history.reviewsN", { n: s.reviews })}</span>}</> : <span className="small muted">{s.error}</span>}</td>
                            <td><span className="row row--nowrap" style={{ justifyContent: "flex-end", gap: "0.4rem" }}>
                              {s.status === "ok" && <Button size="sm" onClick={() => { setQuery({ scan: s.id === r.last_scan_id ? "" : s.id, tab: "findings" }); }}>{t("history.open")}</Button>}
                              {s.status === "ok" && okScans.some((o) => o.id < s.id) && <Button size="sm" onClick={() => setCompare(s.id)}>{t("history.compare")}</Button>}
                            </span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table></div>
                  )}
                  {compare && (diff.loading ? <Loading /> : diff.error ? <ErrorNotice error={diff.error} /> : diff.data && <section aria-label={t("history.compare")}><h3 style={{ marginBottom: "1rem" }}>{t("history.compare")}</h3><DiffView diff={diff.data} /></section>)}
                </div>
              </TabPanel>
              <TabPanel id="res" tab="info" value={tab}>
                <dl className="kv">
                  <dt>{t("form.title")}</dt><dd>{r.title}</dd>
                  <dt>{t("form.kind")}</dt><dd>{t(`kind.${r.kind}`)}</dd>
                  <dt>{t("form.collection")}</dt><dd>{r.collection_name || t("form.noCollection")}</dd>
                  <dt>{t("detail.source")}</dt><dd>{r.url || t("detail.pastedHtml")}</dd>
                  <dt>{t("form.notes")}</dt><dd>{r.notes || "—"}</dd>
                  <dt>{t("schedule.label")}</dt><dd>
                    <label className="row" style={{ gap: "0.6rem" }}>
                      <span className="sr-only">{t("schedule.label")}</span>
                      <select className="select" style={{ width: "auto" }} value={r.schedule} onChange={changeSchedule}>
                        {["off", "daily", "weekly"].map((s) => <option key={s} value={s}>{t(`schedule.${s}`)}</option>)}
                      </select>
                    </label>
                    {r.next_run_at && <span className="muted small">{t("schedule.next", { date: formatDate(r.next_run_at, lang, true) })}</span>}
                  </dd>
                  <dt>{t("detail.created")}</dt><dd>{formatDate(r.created_at, lang, true)}</dd>
                  <dt>{t("detail.engine")}</dt><dd>{current.engine} · {current.duration_ms} {t("detail.ms")} · {Math.round(current.html_bytes / 1024)} {t("detail.kb")}</dd>
                </dl>
              </TabPanel>
            </Panel>
          </>
        )}

      <ResourceForm open={formOpen} onClose={() => setFormOpen(false)} resource={r} collections={collections.data?.items} onSaved={() => { resource.reload(); collections.reload(); }} />
    </div>
  );
}
