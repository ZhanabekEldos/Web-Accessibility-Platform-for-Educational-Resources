import { useState } from "react";
import { api } from "../api.js";
import { useI18n } from "../i18n/index.jsx";
import { Button, ErrorNotice, Field, LinkButton, Panel } from "./ui.jsx";
import { Link } from "../router.jsx";

/** Сканирование сайта целиком: найти страницы → выбрать → добавить в коллекцию и проверить. */
export function CrawlForm() {
  const { t } = useI18n();
  const [url, setUrl] = useState("");
  const [limit, setLimit] = useState(15);
  const [depth, setDepth] = useState(1);
  const [urlError, setUrlError] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [found, setFound] = useState(null);
  const [picked, setPicked] = useState({});
  const [name, setName] = useState("");
  const [schedule, setSchedule] = useState("off");
  const [done, setDone] = useState(null);

  const discover = async (e) => {
    e.preventDefault();
    setError(null); setUrlError(""); setDone(null);
    if (!url.trim()) { setUrlError(t("form.needUrl")); return; }
    setBusy(true);
    try {
      const res = await api.post("/crawl/discover", { url: url.trim(), limit: Number(limit), depth: Number(depth) });
      setFound(res);
      setPicked(Object.fromEntries(res.pages.map((p) => [p.url, !p.exists])));
      setName(new URL(res.root).hostname.replace(/^www\./, ""));
    } catch (err) { setError(err); setFound(null); } finally { setBusy(false); }
  };

  const chosen = found ? found.pages.filter((p) => picked[p.url]) : [];
  const allOn = found && found.pages.every((p) => picked[p.url]);

  const importPages = async () => {
    setError(null); setBusy(true);
    try {
      const res = await api.post("/crawl/import", { pages: chosen.map((p) => ({ url: p.url, title: p.title })), collection_name: name.trim() || undefined, schedule, scan: true });
      setDone(res); setFound(null);
    } catch (err) { setError(err); } finally { setBusy(false); }
  };

  return (
    <div className="stack-lg">
      <form className="panel stack" onSubmit={discover} noValidate>
        <p className="muted">{t("crawl.lead")}</p>
        <Field label={t("crawl.url")} hint={t("crawl.urlHint")} error={urlError}>{(p) => <input {...p} className="input" type="url" inputMode="url" placeholder="https://" value={url} onChange={(e) => setUrl(e.target.value)} />}</Field>
        <div className="grid grid--2">
          <Field label={t("crawl.limit")}>{(p) => <select {...p} className="select" value={limit} onChange={(e) => setLimit(e.target.value)}>{[5, 10, 15, 25, 50].map((n) => <option key={n} value={n}>{n}</option>)}</select>}</Field>
          <Field label={t("crawl.depth")} hint={t("crawl.depthHint")}>{(p) => <select {...p} className="select" value={depth} onChange={(e) => setDepth(e.target.value)}><option value={1}>{t("crawl.depth1")}</option><option value={2}>{t("crawl.depth2")}</option></select>}</Field>
        </div>
        <div><Button variant="primary" type="submit" icon="globe" busy={busy && !found}>{t("crawl.find")}</Button></div>
      </form>

      {error && <ErrorNotice error={error} />}

      {found && (
        <Panel title={t("crawl.found", { n: found.pages.length })}>
          <div className="stack">
            <label className="check"><input type="checkbox" checked={allOn} onChange={(e) => setPicked(Object.fromEntries(found.pages.map((p) => [p.url, e.target.checked])))} />{t("crawl.selectAll")}</label>
            <ul className="plain-list plain-list--stack crawl-list" aria-label={t("crawl.pages")}>
              {found.pages.map((p) => (
                <li key={p.url}>
                  <label className="check"><input type="checkbox" checked={!!picked[p.url]} onChange={(e) => setPicked({ ...picked, [p.url]: e.target.checked })} />
                    <span><strong>{p.title || p.url}</strong>{p.exists && <> <span className="badge badge--neutral">{t("crawl.exists")}</span></>}<span className="crawl-list__url">{p.url}</span></span>
                  </label>
                </li>
              ))}
            </ul>
            <div className="grid grid--2">
              <Field label={t("crawl.collection")} hint={t("crawl.collectionHint")}>{(p) => <input {...p} className="input" maxLength={120} value={name} onChange={(e) => setName(e.target.value)} />}</Field>
              <Field label={t("schedule.label")} hint={t("schedule.hint")}>{(p) => (
                <select {...p} className="select" value={schedule} onChange={(e) => setSchedule(e.target.value)}>
                  {["off", "daily", "weekly"].map((s) => <option key={s} value={s}>{t(`schedule.${s}`)}</option>)}
                </select>)}</Field>
            </div>
            <div className="row">
              <Button variant="primary" icon="check" busy={busy} disabled={chosen.length === 0} onClick={importPages}>{t("crawl.run", { n: chosen.length })}</Button>
              <Button onClick={() => setFound(null)}>{t("common.cancel")}</Button>
            </div>
          </div>
        </Panel>
      )}

      {done && (
        <Panel title={t("crawl.doneTitle")}>
          <div className="stack">
            <p>{t("crawl.doneText", { created: done.created, skipped: done.skipped, ok: done.ok, failed: done.failed })}</p>
            {done.results?.some((r) => !r.ok) && (
              <ul className="bullets">{done.results.filter((r) => !r.ok).map((r) => <li key={r.resource_id}><Link to={`/resources/${r.resource_id}`}>#{r.resource_id}</Link>: {r.error}</li>)}</ul>
            )}
            <div className="row">
              <LinkButton to={done.collection_id ? `/resources?collection=${done.collection_id}` : "/resources"} variant="primary">{t("crawl.open")}</LinkButton>
              <LinkButton to="/">{t("nav.dashboard")}</LinkButton>
            </div>
          </div>
        </Panel>
      )}
    </div>
  );
}
