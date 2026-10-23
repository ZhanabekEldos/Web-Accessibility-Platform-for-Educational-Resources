import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import { useConfirm } from "../components/Dialog.jsx";
import { ResourceForm } from "../components/ResourceForm.jsx";
import { useToast } from "../components/Toast.jsx";
import { BandBadge, Button, EmptyState, ErrorNotice, Field, LevelBadge, Loading, PageHead, Pagination, ScoreMark } from "../components/ui.jsx";
import { formatDate } from "../format.js";
import { useApi, useDebounced, usePageTitle } from "../hooks.js";
import { useI18n } from "../i18n/index.jsx";
import { Link, useQueryState } from "../router.jsx";

const SORTS = { title: "title", score: "score", scanned: "scanned", updated: "updated" };

export default function Resources() {
  const { t, lang } = useI18n();
  const toast = useToast();
  const confirm = useConfirm();
  usePageTitle(t("nav.resources"));
  const [query, setQuery] = useQueryState();
  const [search, setSearch] = useState(query.get("q") || "");
  const debounced = useDebounced(search);
  const params = {
    q: query.get("q") || "", collection_id: query.get("collection") || "", kind: query.get("kind") || "", band: query.get("band") || "",
    sort: query.get("sort") || "updated", order: query.get("order") || "desc", page: query.get("page") || 1, per_page: 15,
  };
  useEffect(() => { if (debounced !== (query.get("q") || "")) setQuery({ q: debounced, page: "" }); }, [debounced]); // eslint-disable-line
  const list = useApi("/resources", params);
  const collections = useApi("/collections");
  const [formOpen, setFormOpen] = useState(false);
  const [selected, setSelected] = useState(new Set());
  const [busy, setBusy] = useState(new Set());
  const [bulkBusy, setBulkBusy] = useState(false);
  useEffect(() => setSelected(new Set()), [list.data]);

  const items = list.data?.items || [];
  const allSelected = items.length > 0 && items.every((r) => selected.has(r.id));
  const toggle = (id) => setSelected((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const sortBy = (key) => setQuery({ sort: key, order: params.sort === key && params.order === "asc" ? "desc" : "asc", page: "" });
  const ariaSort = (key) => (params.sort === key ? (params.order === "asc" ? "ascending" : "descending") : "none");

  const scan = async (r) => {
    setBusy((b) => new Set(b).add(r.id));
    try { const res = await api.post(`/resources/${r.id}/scan`); toast(t("resources.scanned", { title: r.title, score: Math.round(res.score) })); list.reload(); }
    catch (e) { toast(e.message, { type: "error" }); list.reload(); }
    finally { setBusy((b) => { const n = new Set(b); n.delete(r.id); return n; }); }
  };
  const remove = async (r) => {
    if (!(await confirm({ title: t("resources.deleteTitle"), body: t("resources.deleteBody", { title: r.title }), confirmLabel: t("common.delete"), danger: true }))) return;
    try { await api.del(`/resources/${r.id}`); toast(t("resources.deleted")); list.reload(); collections.reload(); } catch (e) { toast(e.message, { type: "error" }); }
  };
  const bulkScan = async () => {
    setBulkBusy(true);
    try {
      const res = await api.post("/scans/batch", { resource_ids: [...selected] });
      toast(t("resources.bulkDone", { ok: res.ok, failed: res.failed }), { type: res.failed ? "error" : "info" });
      list.reload();
    } catch (e) { toast(e.message, { type: "error" }); } finally { setBulkBusy(false); }
  };

  const hasFilters = params.q || params.collection_id || params.kind || params.band;
  const SortHead = ({ k, children }) => <th scope="col" aria-sort={ariaSort(k)}><button type="button" onClick={() => sortBy(k)}>{children}<span aria-hidden="true">{params.sort === k ? (params.order === "asc" ? "▲" : "▼") : ""}</span></button></th>;

  return (
    <div className="stack-lg">
      <PageHead title={t("resources.title")} actions={<Button variant="primary" icon="plus" onClick={() => setFormOpen(true)}>{t("resources.add")}</Button>}>{t("resources.lead")}</PageHead>

      <div className="filters" role="search" aria-label={t("findings.filters")}>
        <Field label={t("resources.search")} className="field--search">{(p) => <input {...p} className="input" type="search" value={search} onChange={(e) => setSearch(e.target.value)} />}</Field>
        <Field label={t("resources.collection")}>{(p) => (
          <select {...p} className="select" value={params.collection_id} onChange={(e) => setQuery({ collection: e.target.value, page: "" })}>
            <option value="">{t("common.any")}</option><option value="none">{t("resources.noCollection")}</option>
            {collections.data?.items.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>)}</Field>
        <Field label={t("resources.kind")}>{(p) => (
          <select {...p} className="select" value={params.kind} onChange={(e) => setQuery({ kind: e.target.value, page: "" })}>
            <option value="">{t("common.any")}</option>
            {["course", "lesson", "material", "portal", "page", "other"].map((k) => <option key={k} value={k}>{t(`kind.${k}`)}</option>)}
          </select>)}</Field>
        <Field label={t("resources.band")}>{(p) => (
          <select {...p} className="select" value={params.band} onChange={(e) => setQuery({ band: e.target.value, page: "" })}>
            <option value="">{t("common.any")}</option>
            {["good", "fair", "poor", "unscanned"].map((b) => <option key={b} value={b}>{t(b === "unscanned" ? "band.none" : `band.${b}`)}</option>)}
          </select>)}</Field>
      </div>

      {selected.size > 0 && (
        <div className="notice notice--info" role="region" aria-label={t("resources.bulk")}>
          <span className="grow">{t("resources.selected", { n: selected.size })}</span>
          <Button size="sm" variant="primary" busy={bulkBusy} onClick={bulkScan}>{t("resources.scanSelected")}</Button>
        </div>
      )}

      {list.error ? <ErrorNotice error={list.error} onRetry={list.reload} />
        : list.loading && !list.data ? <Loading />
        : items.length === 0 ? (
          <EmptyState title={t(hasFilters ? "resources.noMatch" : "resources.emptyTitle")} actions={hasFilters ? <Button onClick={() => { setSearch(""); setQuery({ q: "", collection: "", kind: "", band: "", page: "" }); }}>{t("resources.reset")}</Button> : <Button variant="primary" icon="plus" onClick={() => setFormOpen(true)}>{t("resources.add")}</Button>}>
            {t(hasFilters ? "resources.noMatchText" : "resources.emptyText")}
          </EmptyState>
        ) : (
          <>
            <div className="table-wrap" aria-busy={list.loading}>
              <table className="table">
                <caption className="sr-only">{t("resources.title")}</caption>
                <thead><tr>
                  <th scope="col"><input type="checkbox" aria-label={t("resources.selectAll")} checked={allSelected} onChange={() => setSelected(allSelected ? new Set() : new Set(items.map((r) => r.id)))} /></th>
                  <SortHead k="title">{t("resources.colTitle")}</SortHead>
                  <SortHead k="score">{t("resources.colScore")}</SortHead>
                  <th scope="col">{t("resources.colLevel")}</th>
                  <th scope="col">{t("resources.colIssues")}</th>
                  <SortHead k="scanned">{t("resources.colScanned")}</SortHead>
                  <th scope="col"><span className="sr-only">{t("common.actions")}</span></th>
                </tr></thead>
                <tbody>
                  {items.map((r) => (
                    <tr key={r.id}>
                      <td><input type="checkbox" aria-label={t("resources.select", { title: r.title })} checked={selected.has(r.id)} onChange={() => toggle(r.id)} /></td>
                      <th scope="row" style={{ fontWeight: "inherit" }}>
                        <Link to={`/resources/${r.id}`} className="rowlink cell-title">{r.title}</Link>
                        <div className="cell-sub">{t(`kind.${r.kind}`)}{r.collection_name ? ` · ${r.collection_name}` : ""}{r.url ? ` · ${r.url}` : ""}</div>
                      </th>
                      <td>{r.last_score == null ? <BandBadge score={null} /> : <span className="row" style={{ gap: "0.6rem" }}><ScoreMark score={r.last_score} size="sm" /><BandBadge score={r.last_score} /></span>}</td>
                      <td>{r.last_score == null ? "—" : <LevelBadge level={r.last_level} />}</td>
                      <td className="num">{r.last_score == null ? "—" : r.last_violations}{r.last_status === "error" ? ` ${t("resources.failed")}` : ""}</td>
                      <td className="nowrap small muted">{formatDate(r.last_scan_at, lang)}</td>
                      <td><span className="row row--nowrap" style={{ gap: "0.4rem", justifyContent: "flex-end" }}>
                        <Button size="sm" busy={busy.has(r.id)} onClick={() => scan(r)} aria-label={`${t("resources.scan")}: ${r.title}`}>{t("resources.scan")}</Button>
                        <Button size="sm" variant="ghost" className="btn--icon" icon="trash" onClick={() => remove(r)} aria-label={`${t("common.delete")}: ${r.title}`} />
                      </span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={list.data.page} pages={list.data.pages} total={list.data.total} onPage={(p) => setQuery({ page: p })} />
          </>
        )}

      <ResourceForm open={formOpen} onClose={() => setFormOpen(false)} collections={collections.data?.items} defaultCollectionId={params.collection_id && params.collection_id !== "none" ? Number(params.collection_id) : undefined} onSaved={() => { list.reload(); collections.reload(); }} />
    </div>
  );
}
