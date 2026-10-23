import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useI18n } from "../i18n/index.jsx";
import { Dialog } from "./Dialog.jsx";
import { useToast } from "./Toast.jsx";
import { Button, ErrorNotice, Field } from "./ui.jsx";

const KINDS = ["course", "lesson", "material", "portal", "page", "other"];

/** Создание и редактирование ресурса. Ошибки сервера показываются у соответствующих полей. */
export function ResourceForm({ open, onClose, resource, collections, defaultCollectionId, onSaved }) {
  const { t } = useI18n();
  const toast = useToast();
  const editing = !!resource;
  const [form, setForm] = useState(null);
  const [source, setSource] = useState("url");
  const [scanNow, setScanNow] = useState(true);
  const [errors, setErrors] = useState({});
  const [failure, setFailure] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    setErrors({}); setFailure(null); setBusy(false);
    const base = { title: "", kind: "page", url: "", html: "", collection_id: defaultCollectionId ?? "", notes: "" };
    if (!editing) { setForm(base); setSource("url"); setScanNow(true); return; }
    setForm({ ...base, title: resource.title, kind: resource.kind, url: resource.url || "", collection_id: resource.collection_id ?? "", notes: resource.notes || "" });
    setSource(resource.url ? "url" : "html");
    if (resource.has_html && !resource.url) {
      api.get(`/resources/${resource.id}`, { source: 1 }).then((r) => setForm((f) => f && { ...f, html: r.html || "" })).catch(() => {});
    }
  }, [open, editing, resource, defaultCollectionId]);

  if (!form) return <Dialog open={false} onClose={onClose} title="" />;
  const set = (patch) => setForm((f) => ({ ...f, ...patch }));

  const submit = async (e) => {
    e.preventDefault();
    const payload = {
      title: form.title, kind: form.kind, notes: form.notes,
      collection_id: form.collection_id === "" ? null : Number(form.collection_id),
      url: source === "url" ? form.url.trim() || null : null,
      html: source === "html" ? form.html : null,
    };
    if (!payload.url && !(payload.html || "").trim()) {
      setErrors({ source: t(source === "url" ? "form.needUrl" : "form.needHtml") });
      return;
    }
    setBusy(true); setErrors({}); setFailure(null);
    try {
      const result = editing ? await api.patch(`/resources/${resource.id}`, payload) : await api.post("/resources", payload, scanNow ? { scan: 1 } : undefined);
      toast(t(editing ? "form.saved" : "form.created"));
      if (!editing && result.scan_error) toast(result.scan_error.message, { type: "error" });
      onSaved?.(result);
      onClose();
    } catch (err) {
      if (err.details?.length) setErrors(Object.fromEntries(err.details.map((d) => [d.field, d.message])));
      else setFailure(err);
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title={t(editing ? "form.editTitle" : "form.addTitle")} wide>
      <form className="stack" onSubmit={submit} noValidate>
        {failure && <ErrorNotice error={failure} />}
        <Field label={t("form.title")} error={errors.title}>{(p) => <input {...p} className="input" required maxLength={200} value={form.title} onChange={(e) => set({ title: e.target.value })} autoFocus />}</Field>
        <div className="grid grid--2">
          <Field label={t("form.kind")}>{(p) => <select {...p} className="select" value={form.kind} onChange={(e) => set({ kind: e.target.value })}>{KINDS.map((k) => <option key={k} value={k}>{t(`kind.${k}`)}</option>)}</select>}</Field>
          <Field label={t("form.collection")}>{(p) => (
            <select {...p} className="select" value={form.collection_id} onChange={(e) => set({ collection_id: e.target.value })}>
              <option value="">{t("form.noCollection")}</option>
              {collections?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>)}</Field>
        </div>
        <div className="stack" style={{ gap: "0.5rem" }}>
          <div className="seg-control" role="group" aria-label={t("form.source")} style={{ justifySelf: "start" }}>
            <button type="button" aria-pressed={source === "url"} onClick={() => setSource("url")}>{t("form.sourceUrl")}</button>
            <button type="button" aria-pressed={source === "html"} onClick={() => setSource("html")}>{t("form.sourceHtml")}</button>
          </div>
          {source === "url"
            ? <Field label={t("form.url")} hint={t("form.urlHint")} error={errors.url || errors.source}>{(p) => <input {...p} className="input" type="url" inputMode="url" placeholder="https://" value={form.url} onChange={(e) => set({ url: e.target.value })} />}</Field>
            : <Field label={t("form.html")} hint={t("form.htmlHint")} error={errors.html || errors.source}>{(p) => <textarea {...p} className="textarea" spellCheck={false} value={form.html} onChange={(e) => set({ html: e.target.value })} />}</Field>}
        </div>
        <Field label={t("form.notes")} error={errors.notes}>{(p) => <input {...p} className="input" maxLength={2000} value={form.notes} onChange={(e) => set({ notes: e.target.value })} />}</Field>
        {!editing && <label className="check"><input type="checkbox" checked={scanNow} onChange={(e) => setScanNow(e.target.checked)} />{t("form.scanNow")}</label>}
        <div className="dialog__actions">
          <Button onClick={onClose}>{t("common.cancel")}</Button>
          <Button variant="primary" type="submit" busy={busy}>{t(editing ? "common.save" : "form.add")}</Button>
        </div>
      </form>
    </Dialog>
  );
}
