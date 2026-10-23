import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { Tabs, TabPanel } from "../components/Tabs.jsx";
import { FindingsView, PlanView, ScanVerdict } from "../components/ScanReport.jsx";
import { CrawlForm } from "../components/CrawlForm.jsx";
import { Button, ErrorNotice, Field, LinkButton, PageHead, Panel } from "../components/ui.jsx";
import { usePageTitle, useApi } from "../hooks.js";
import { useI18n } from "../i18n/index.jsx";

export default function Check() {
  const { t } = useI18n();
  usePageTitle(t("nav.check"));
  const collections = useApi("/collections");
  const [source, setSource] = useState("url");
  const [url, setUrl] = useState("");
  const [html, setHtml] = useState("");
  const [save, setSave] = useState(false);
  const [title, setTitle] = useState("");
  const [collectionId, setCollectionId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [sourceError, setSourceError] = useState("");
  const [titleError, setTitleError] = useState("");
  const [scan, setScan] = useState(null);
  const [tab, setTab] = useState("findings");
  const [focusRule, setFocusRule] = useState(null);
  const result = useRef(null);
  const [mode, setMode] = useState("page");

  useEffect(() => { if (scan) result.current?.focus(); }, [scan]);

  const submit = async (e) => {
    e.preventDefault();
    setError(null); setSourceError(""); setTitleError("");
    const value = source === "url" ? url.trim() : html;
    if (!value.trim()) { setSourceError(t(source === "url" ? "form.needUrl" : "form.needHtml")); return; }
    if (save && !title.trim()) { setTitleError(t("check.needTitle")); return; }
    setBusy(true);
    try {
      const body = source === "url" ? { url: value } : { html: value };
      if (save) body.save_as = { title: title.trim(), kind: "page", collection_id: collectionId === "" ? null : Number(collectionId) };
      setScan(await api.post("/scans", body));
      setTab("findings"); setFocusRule(null);
    } catch (err) { setError(err); setScan(null); } finally { setBusy(false); }
  };

  return (
    <div className="stack-lg">
      <PageHead title={t("check.title")}>{t("check.lead")}</PageHead>
      <div className="seg-control" role="group" aria-label={t("check.mode")} style={{ justifySelf: "start" }}>
        <button type="button" aria-pressed={mode === "page"} onClick={() => setMode("page")}>{t("check.modePage")}</button>
        <button type="button" aria-pressed={mode === "site"} onClick={() => setMode("site")}>{t("check.modeSite")}</button>
      </div>
      {mode === "site" ? <CrawlForm /> : <>
      <form className="panel stack" onSubmit={submit} noValidate>
        <div className="seg-control" role="group" aria-label={t("form.source")} style={{ justifySelf: "start" }}>
          <button type="button" aria-pressed={source === "url"} onClick={() => setSource("url")}>{t("form.sourceUrl")}</button>
          <button type="button" aria-pressed={source === "html"} onClick={() => setSource("html")}>{t("form.sourceHtml")}</button>
        </div>
        {source === "url"
          ? <Field label={t("form.url")} hint={t("form.urlHint")} error={sourceError}>{(p) => <input {...p} className="input" type="url" inputMode="url" placeholder="https://" value={url} onChange={(e) => setUrl(e.target.value)} />}</Field>
          : <Field label={t("form.html")} hint={t("form.htmlHint")} error={sourceError}>{(p) => <textarea {...p} className="textarea" style={{ minHeight: "14rem" }} spellCheck={false} value={html} onChange={(e) => setHtml(e.target.value)} />}</Field>}
        <label className="check"><input type="checkbox" checked={save} onChange={(e) => setSave(e.target.checked)} />{t("check.save")}</label>
        {save && (
          <div className="grid grid--2">
            <Field label={t("form.title")} error={titleError}>{(p) => <input {...p} className="input" maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} />}</Field>
            <Field label={t("form.collection")}>{(p) => (
              <select {...p} className="select" value={collectionId} onChange={(e) => setCollectionId(e.target.value)}>
                <option value="">{t("form.noCollection")}</option>
                {collections.data?.items.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>)}</Field>
          </div>
        )}
        <div><Button variant="primary" type="submit" icon="check" busy={busy}>{busy ? t("check.running") : t("check.run")}</Button></div>
      </form>

      {error && <ErrorNotice error={error} />}

      {scan && (
        <div className="stack-lg">
          <div className="row-between">
            <h2 ref={result} tabIndex={-1} style={{ outline: "none" }}>{scan.page_title || scan.url || t("check.result")}</h2>
            {scan.resource_id && <LinkButton to={`/resources/${scan.resource_id}`}>{t("check.openResource")}</LinkButton>}
          </div>
          <ScanVerdict scan={scan} />
          <Panel>
            <Tabs id="chk" label={t("report.sections")} value={tab} onChange={setTab} tabs={[{ id: "findings", label: t("tab.findings"), count: scan.violations + scan.reviews }, { id: "plan", label: t("tab.plan") }]} />
            <TabPanel id="chk" tab="findings" value={tab}><FindingsView scan={scan} resourceId={scan.resource_id} focusRule={focusRule} onClearFocus={() => setFocusRule(null)} /></TabPanel>
            <TabPanel id="chk" tab="plan" value={tab}><PlanView scan={scan} onShowRule={(r) => { setFocusRule(r); setTab("findings"); }} /></TabPanel>
          </Panel>
        </div>
      )}
      </>}
    </div>
  );
}
