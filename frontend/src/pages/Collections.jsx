import { useState } from "react";
import { api } from "../api.js";
import { useConfirm, Dialog } from "../components/Dialog.jsx";
import { Menu } from "../components/Menu.jsx";
import { useToast } from "../components/Toast.jsx";
import { Button, EmptyState, ErrorNotice, Field, LinkButton, Loading, PageHead, ScoreMark } from "../components/ui.jsx";
import { useApi, usePageTitle } from "../hooks.js";
import { useI18n } from "../i18n/index.jsx";
import { Link } from "../router.jsx";

export default function Collections() {
  const { t, lang } = useI18n();
  const toast = useToast();
  const confirm = useConfirm();
  usePageTitle(t("nav.collections"));
  const list = useApi("/collections");
  const [editing, setEditing] = useState(null); // null | {} (новая) | {id,...}
  const [form, setForm] = useState({ name: "", description: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(null);

  const open = (c) => { setEditing(c || {}); setForm({ name: c?.name || "", description: c?.description || "" }); setError(""); };
  const submit = async (e) => {
    e.preventDefault();
    try {
      if (editing.id) await api.patch(`/collections/${editing.id}`, form); else await api.post("/collections", form);
      toast(t("collections.saved")); setEditing(null); list.reload();
    } catch (err) { setError(err.message); }
  };
  const remove = async (c) => {
    if (!(await confirm({ title: t("collections.deleteTitle"), body: t("collections.deleteBody", { name: c.name }), confirmLabel: t("common.delete"), danger: true }))) return;
    try { await api.del(`/collections/${c.id}`); toast(t("collections.deleted")); list.reload(); } catch (err) { toast(err.message, { type: "error" }); }
  };
  const scanAll = async (c) => {
    setBusy(c.id);
    try {
      const res = await api.post("/scans/batch", { collection_id: c.id });
      toast(t("resources.bulkDone", { ok: res.ok, failed: res.failed }), { type: res.failed ? "error" : "info" });
      list.reload();
    } catch (err) { toast(err.message, { type: "error" }); } finally { setBusy(null); }
  };

  const items = list.data?.items || [];
  return (
    <div className="stack-lg">
      <PageHead title={t("collections.title")} actions={<Button variant="primary" icon="plus" onClick={() => open()}>{t("collections.add")}</Button>}>{t("collections.lead")}</PageHead>
      {list.error ? <ErrorNotice error={list.error} onRetry={list.reload} /> : list.loading && !list.data ? <Loading /> : items.length === 0 ? (
        <EmptyState title={t("collections.emptyTitle")} actions={<Button variant="primary" icon="plus" onClick={() => open()}>{t("collections.add")}</Button>}>{t("collections.emptyText")}</EmptyState>
      ) : (
        <div className="table-wrap"><table className="table">
          <caption className="sr-only">{t("collections.title")}</caption>
          <thead><tr><th scope="col">{t("collections.name")}</th><th scope="col">{t("collections.resources")}</th><th scope="col">{t("collections.avg")}</th><th scope="col"><span className="sr-only">{t("common.actions")}</span></th></tr></thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.id}>
                <th scope="row" style={{ fontWeight: "inherit" }}><Link className="rowlink cell-title" to={`/resources?collection=${c.id}`}>{c.name}</Link>{c.description && <div className="cell-sub">{c.description}</div>}</th>
                <td className="num">{c.resources_count}</td>
                <td>{c.avg_score == null ? "—" : <ScoreMark score={c.avg_score} size="sm" />}</td>
                <td><span className="row row--nowrap" style={{ justifyContent: "flex-end", gap: "0.4rem" }}>
                  <Button size="sm" busy={busy === c.id} disabled={!c.resources_count} onClick={() => scanAll(c)}>{t("collections.scanAll")}</Button>
                  {c.resources_count > 0 && <Menu label={t("collections.report")} icon="download">
                    <a href={`/api/collections/${c.id}/report?format=html&lang=${lang}`} download>{t("detail.export.html")}</a>
                    <a href={`/api/collections/${c.id}/report?format=csv&lang=${lang}`} download>{t("detail.export.csv")}</a>
                  </Menu>}
                  <Button size="sm" variant="ghost" className="btn--icon" icon="edit" aria-label={`${t("common.edit")}: ${c.name}`} onClick={() => open(c)} />
                  <Button size="sm" variant="ghost" className="btn--icon" icon="trash" aria-label={`${t("common.delete")}: ${c.name}`} onClick={() => remove(c)} />
                </span></td>
              </tr>
            ))}
          </tbody>
        </table></div>
      )}
      <Dialog open={!!editing} onClose={() => setEditing(null)} title={t(editing?.id ? "collections.editTitle" : "collections.addTitle")}>
        <form className="stack" onSubmit={submit} noValidate>
          <Field label={t("collections.name")} error={error}>{(p) => <input {...p} className="input" required maxLength={120} autoFocus value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />}</Field>
          <Field label={t("collections.description")}>{(p) => <input {...p} className="input" maxLength={500} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />}</Field>
          <div className="dialog__actions"><Button onClick={() => setEditing(null)}>{t("common.cancel")}</Button><Button variant="primary" type="submit">{t("common.save")}</Button></div>
        </form>
      </Dialog>
    </div>
  );
}
