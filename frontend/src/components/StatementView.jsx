import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useApi, useDebounced, copyText } from "../hooks.js";
import { useI18n } from "../i18n/index.jsx";
import { Button, ErrorNotice, Field, Loading, Panel } from "./ui.jsx";
import { useToast } from "./Toast.jsx";

const KEY = "accessedu.statement";
const load = () => { try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch { return {}; } };

export function StatementView({ resource }) {
  const { t, lang } = useI18n();
  const toast = useToast();
  const saved = load();
  const [org, setOrg] = useState(saved.org || "");
  const [contact, setContact] = useState(saved.contact || "");
  const dOrg = useDebounced(org), dContact = useDebounced(contact);
  useEffect(() => { try { localStorage.setItem(KEY, JSON.stringify({ org: dOrg, contact: dContact })); } catch { /* хранилище недоступно */ } }, [dOrg, dContact]);
  const doc = useApi(`/resources/${resource.id}/statement`, { organization: dOrg, contact: dContact });

  const qs = new URLSearchParams({ organization: org, contact, lang });
  const href = (format) => `/api/resources/${resource.id}/statement?${qs}&format=${format}`;
  const badgeUrl = `${window.location.origin}/api/resources/${resource.id}/badge.svg?lang=${lang}`;
  const badgeAlt = lang === "ru" ? "Оценка доступности" : "Accessibility score";
  const embed = `<a href="${window.location.origin}/resources/${resource.id}"><img src="${badgeUrl}" alt="${badgeAlt}"></a>`;
  const copy = async (text, ok) => toast(await copyText(text) ? ok : t("statement.copyFailed"), { type: "info" });
  const copyHtml = async () => {
    try { const res = await fetch(href("html")); await copy(await res.text(), t("statement.copiedHtml")); } catch { toast(t("statement.copyFailed"), { type: "error" }); }
  };

  return (
    <div className="stack-lg">
      <div className="howto"><strong>{t("statement.leadTitle")}</strong>{t("statement.lead")}</div>
      <div className="grid grid--2">
        <Field label={t("statement.org")} hint={t("statement.orgHint")}>{(p) => <input {...p} className="input" maxLength={160} value={org} onChange={(e) => setOrg(e.target.value)} />}</Field>
        <Field label={t("statement.contact")} hint={t("statement.contactHint")}>{(p) => <input {...p} className="input" maxLength={160} value={contact} onChange={(e) => setContact(e.target.value)} />}</Field>
      </div>
      {doc.error ? <ErrorNotice error={doc.error} onRetry={doc.reload} /> : !doc.data ? <Loading /> : (
        <article className="statement" aria-label={t("statement.preview")}>
          <h3>{doc.data.title}: {doc.data.resource}</h3>
          {doc.data.sections.map((s, i) => (
            <section key={i}>
              {s.heading && <h4>{s.heading}</h4>}
              {s.paragraphs?.map((p, j) => <p key={j}>{p}</p>)}
              {s.items && <ul className="bullets">{s.items.map((x, j) => <li key={j}>{x}</li>)}</ul>}
            </section>
          ))}
          <p className="muted small">{doc.data.footer}</p>
          <p className="muted small">{doc.data.note}</p>
        </article>
      )}
      <div className="row">
        <a className="btn btn--primary" href={href("html")} download>{t("statement.downloadHtml")}</a>
        <a className="btn" href={href("md")} download>{t("statement.downloadMd")}</a>
        <Button icon="copy" onClick={copyHtml}>{t("statement.copyHtml")}</Button>
      </div>
      <Panel title={t("statement.badge")}>
        <p className="muted" style={{ marginBottom: "0.8rem" }}>{t("statement.badgeLead")}</p>
        <p style={{ marginBottom: "0.8rem" }}><img src={`/api/resources/${resource.id}/badge.svg?lang=${lang}&v=${resource.last_scan_id || 0}`} alt={`${badgeAlt}: ${resource.last_score == null ? "—" : Math.round(resource.last_score)}${resource.last_level ? ` · ${resource.last_level}` : ""}`} height="22" /></p>
        <label className="field"><span className="field__label">{t("statement.embed")}</span>
          <textarea className="textarea" readOnly rows={3} value={embed} onFocus={(e) => e.target.select()} /></label>
        <div style={{ marginTop: "0.6rem" }}><Button size="sm" icon="copy" onClick={() => copy(embed, t("statement.copiedEmbed"))}>{t("statement.copyEmbed")}</Button></div>
      </Panel>
    </div>
  );
}
