import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { useI18n } from "../i18n/index.jsx";
import { useApi } from "../hooks.js";
import { Button, ErrorNotice, Loading } from "./ui.jsx";
import { useToast } from "./Toast.jsx";

const PRINCIPLES = ["perceivable", "operable", "understandable", "robust"];
const STATUSES = ["pass", "fail", "na"];

function Item({ item, resourceId, onChange }) {
  const { t } = useI18n();
  const toast = useToast();
  const [note, setNote] = useState(item.note);
  useEffect(() => setNote(item.note), [item.note]);

  const save = async (status, text = note) => {
    try { onChange(await api.put(`/resources/${resourceId}/audit/${item.id}`, { status, note: text })); }
    catch (e) { toast(e.message, { type: "error" }); }
  };
  return (
    <li className={`audit-item${item.status ? ` audit-item--${item.status}` : ""}`}>
      <fieldset>
        <legend>
          <span className="audit-item__title">{item.title}</span>
          {item.education && <span className="badge badge--accent">{t("audit.education")}</span>}
        </legend>
        <p className="muted small">{item.how}</p>
        <p className="row small" style={{ gap: "0.4rem" }}>
          {item.wcag.map((c) => <a key={c.id} className="chip" href={c.url} target="_blank" rel="noreferrer noopener">{c.id}<span className="sr-only"> {c.name} ({t("common.newTab")})</span></a>)}
        </p>
        <div className="row" style={{ gap: "0.75rem" }}>
          <div className="radio-seg" role="radiogroup" aria-label={item.title}>
            {STATUSES.map((s) => (
              <label key={s} className={`radio-seg__opt radio-seg__opt--${s}`}>
                <input type="radio" name={`audit-${item.id}`} checked={item.status === s} onChange={() => save(s)} />
                <span>{s === "pass" ? "✓ " : s === "fail" ? "✕ " : ""}{t(`audit.status.${s}`)}</span>
              </label>
            ))}
          </div>
          {item.status && <Button size="sm" variant="ghost" onClick={() => save(null, "")}>{t("audit.reset")}<span className="sr-only">: {item.title}</span></Button>}
        </div>
        {item.status && (
          <label className="field" style={{ marginTop: "0.6rem" }}>
            <span className="field__label small">{t("audit.note")}</span>
            <input className="input" maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} onBlur={() => { if (note !== item.note) save(item.status, note); }} />
          </label>
        )}
      </fieldset>
    </li>
  );
}

export function AuditView({ resourceId, onProgress }) {
  const { t } = useI18n();
  const audit = useApi(`/resources/${resourceId}/audit`);
  const [data, setData] = useState(null);
  const cb = useRef(onProgress);
  cb.current = onProgress;
  useEffect(() => { if (audit.data) setData(audit.data); }, [audit.data]);
  useEffect(() => { if (data) cb.current?.(data.progress); }, [data]);

  if (audit.error) return <ErrorNotice error={audit.error} onRetry={audit.reload} />;
  if (!data) return <Loading />;
  const p = data.progress;
  return (
    <div className="stack-lg">
      <div className="howto"><strong>{t("audit.leadTitle")}</strong>{t("audit.lead")}</div>
      <div className="progress">
        <div className="row-between"><strong>{t("audit.progress", { done: p.done, total: p.total })}</strong>
          <span className="muted small">{t("audit.counts", { pass: p.pass, fail: p.fail, na: p.na })}</span></div>
        <div className="meter" role="progressbar" aria-label={t("audit.progressLabel")} aria-valuemin={0} aria-valuemax={p.total} aria-valuenow={p.done}>
          <span className="meter__fill meter__fill--good" style={{ width: `${(p.done / p.total) * 100}%` }} />
        </div>
      </div>
      {PRINCIPLES.map((pr) => {
        const items = data.items.filter((i) => i.principle === pr);
        if (!items.length) return null;
        return (
          <section key={pr} className="stack" aria-labelledby={`audit-h-${pr}`}>
            <h3 id={`audit-h-${pr}`}>{t(`principle.${pr}`)}</h3>
            <ul className="plain-list plain-list--stack">{items.map((i) => <Item key={i.id} item={i} resourceId={resourceId} onChange={setData} />)}</ul>
          </section>
        );
      })}
    </div>
  );
}
