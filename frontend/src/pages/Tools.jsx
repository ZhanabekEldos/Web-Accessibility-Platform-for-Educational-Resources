import { useEffect, useState } from "react";
import { api } from "../api.js";
import { TabPanel, Tabs } from "../components/Tabs.jsx";
import { Button, ErrorNotice, Field, PageHead, Panel } from "../components/ui.jsx";
import { formatNumber } from "../format.js";
import { useApi, useDebounced, usePageTitle } from "../hooks.js";
import { useI18n } from "../i18n/index.jsx";
import { useQueryState } from "../router.jsx";

const CHECKS = [
  ["aa_normal", "4.5"], ["aa_large", "3"], ["aa_ui", "3"], ["aaa_normal", "7"], ["aaa_large", "4.5"],
];

function ContrastTool() {
  const { t, lang } = useI18n();
  const [fg, setFg] = useState("#595959");
  const [bg, setBg] = useState("#ffffff");
  const dFg = useDebounced(fg, 250);
  const dBg = useDebounced(bg, 250);
  const [result, setResult] = useState(null);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (!dFg.trim() || !dBg.trim()) return;
    let cancelled = false;
    api.post("/tools/contrast", { fg: dFg, bg: dBg })
      .then((r) => { if (!cancelled) { setResult(r); setErrors({}); } })
      .catch((e) => {
        if (cancelled) return;
        const next = {};
        for (const d of e.details || []) next[d.field] = t(d.field === "fg" ? "contrast.badFg" : "contrast.badBg");
        setErrors(Object.keys(next).length ? next : { fg: e.message });
      });
    return () => { cancelled = true; };
  }, [dFg, dBg, t]);

  const ratio = result ? formatNumber(result.ratio, lang, 2) : "—";
  const passes = (key) => result?.checks[key];
  const bestSuggestion = result?.suggestions.find((s) => s.target === 4.5);

  return (
    <div className="stack-lg">
      <div className="grid grid--2">
        <Panel title={t("contrast.colors")}>
          <div className="stack">
            {[["fg", t("contrast.fg"), fg, setFg, result?.fg], ["bg", t("contrast.bg"), bg, setBg, result?.bg]].map(([key, label, value, set, hex]) => (
              <Field key={key} label={label} hint={t("contrast.hint")} error={errors[key]}>{(p) => (
                <span className="row row--nowrap" style={{ gap: "0.6rem" }}>
                  <input className="color-pick" type="color" aria-label={t("contrast.picker", { name: label })} value={hex || "#000000"} onChange={(e) => set(e.target.value)} />
                  <input {...p} className="input" spellCheck={false} autoComplete="off" value={value} onChange={(e) => set(e.target.value)} />
                </span>)}
              </Field>
            ))}
            <div><Button icon="swap" onClick={() => { setFg(bg); setBg(fg); }}>{t("contrast.swap")}</Button></div>
          </div>
        </Panel>
        <Panel title={t("contrast.result")}>
          <div className="stack">
            <p className="contrast-ratio" role="status" aria-live="polite"><span className="num">{ratio}</span><span className="muted"> : 1</span></p>
            <div className="contrast-sample" style={result ? { color: result.fg, background: result.bg } : undefined} aria-label={t("contrast.sampleLabel")} role="group">
              <p className="contrast-sample__large">{t("contrast.sampleLarge")}</p>
              <p>{t("contrast.sampleText")}</p>
            </div>
            <ul className="checklist" aria-label={t("contrast.checks")}>
              {CHECKS.map(([key, need]) => (
                <li key={key} className={passes(key) ? "is-pass" : "is-fail"}>
                  <span className="checklist__mark" aria-hidden="true">{passes(key) ? "✓" : "✕"}</span>
                  <span>{t(`contrast.check.${key}`)} <span className="muted small">({need.replace(".", lang === "ru" ? "," : ".")} : 1)</span></span>
                  <strong>{result ? t(passes(key) ? "contrast.pass" : "contrast.fail") : "—"}</strong>
                </li>
              ))}
            </ul>
          </div>
        </Panel>
      </div>

      {result && (
        <Panel title={t("contrast.fixTitle")}>
          <p className="muted" style={{ marginBottom: "0.9rem" }}>{t("contrast.fixLead")}</p>
          <ul className="plain-list">
            {result.suggestions.map((s) => (
              <li key={s.target}>
                <span className="row" style={{ gap: "0.75rem" }}>
                  <span className="swatch" style={{ background: s.color, outlineColor: result.fg }} aria-hidden="true" />
                  <span><strong>{t("contrast.toReach", { n: formatNumber(s.target, lang, s.target % 1 ? 1 : 0) })}</strong> <code>{s.color}</code> <span className="muted small">· {formatNumber(s.ratio, lang, 2)} : 1</span></span>
                </span>
                {s.changed ? <Button size="sm" onClick={() => setFg(s.color)}>{t("contrast.apply")}</Button> : <span className="badge badge--good">{t("contrast.already")}</span>}
              </li>
            ))}
          </ul>
          {!bestSuggestion && <p className="muted small">{t("contrast.noFix")}</p>}
        </Panel>
      )}
    </div>
  );
}

function ReadabilityTool() {
  const { t, lang } = useI18n();
  const [mode, setMode] = useState("text");
  const [text, setText] = useState("");
  const [resourceId, setResourceId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [fieldError, setFieldError] = useState("");
  const [result, setResult] = useState(null);
  const resources = useApi("/resources", { per_page: 100, sort: "title", order: "asc" }, { skip: mode !== "resource" });

  const run = async (e) => {
    e.preventDefault();
    setError(null); setFieldError("");
    if (mode === "text" && !text.trim()) { setFieldError(t("read.needText")); return; }
    if (mode === "resource" && !resourceId) { setFieldError(t("read.needResource")); return; }
    setBusy(true);
    try { setResult(await api.post("/tools/readability", mode === "text" ? { text } : { resource_id: Number(resourceId) })); }
    catch (err) { setError(err); setResult(null); } finally { setBusy(false); }
  };

  return (
    <div className="stack-lg">
      <form className="panel stack" onSubmit={run} noValidate>
        <p className="muted">{t("read.lead")}</p>
        <div className="seg-control" role="group" aria-label={t("read.source")} style={{ justifySelf: "start" }}>
          <button type="button" aria-pressed={mode === "text"} onClick={() => setMode("text")}>{t("read.modeText")}</button>
          <button type="button" aria-pressed={mode === "resource"} onClick={() => setMode("resource")}>{t("read.modeResource")}</button>
        </div>
        {mode === "text"
          ? <Field label={t("read.text")} hint={t("read.textHint")} error={fieldError}>{(p) => <textarea {...p} className="textarea" style={{ minHeight: "11rem", fontFamily: "var(--sans)", fontSize: "1rem" }} value={text} onChange={(e) => setText(e.target.value)} />}</Field>
          : <Field label={t("read.resource")} error={fieldError}>{(p) => (
            <select {...p} className="select" value={resourceId} onChange={(e) => setResourceId(e.target.value)}>
              <option value="">{t("read.choose")}</option>
              {resources.data?.items.map((r) => <option key={r.id} value={r.id}>{r.title}</option>)}
            </select>)}</Field>}
        <div><Button variant="primary" type="submit" icon="check" busy={busy}>{t("read.run")}</Button></div>
      </form>
      {error && <ErrorNotice error={error} />}
      {result && <ReadabilityResult r={result} lang={lang} />}
    </div>
  );
}

function ReadabilityResult({ r, lang }) {
  const { t } = useI18n();
  if (!r.enough) return <div className="notice notice--info" role="status">{t("read.tooShort", { n: r.hints[0].data.min })}</div>;
  const tone = r.flesch >= 60 ? "good" : r.flesch >= 40 ? "fair" : "poor";
  return (
    <div className="stack-lg" role="region" aria-label={t("read.resultLabel")}>
      <Panel>
        <div className="verdict">
          <div>
            <p className="muted small">{t("read.flesch")}</p>
            <p className={`read-score read-score--${tone}`}><span className="num">{formatNumber(r.flesch, lang, 0)}</span><span className="muted small"> / 100</span></p>
            <span className={`badge badge--${tone}`}>{t(`read.band.${r.band}`)}</span>
          </div>
          <div className="verdict__text">
            <div className="meter" role="img" aria-label={t("read.meterLabel", { score: formatNumber(r.flesch, lang, 0), band: t(`read.band.${r.band}`) })}>
              <span className="meter__fill" style={{ width: `${r.flesch}%` }} />
              <span className="meter__mark" style={{ left: "60%" }} />
            </div>
            <p className="muted small">{t("read.target")}</p>
            <p>{r.meets_315 ? t("read.meets") : t("read.notMeets")}</p>
          </div>
        </div>
      </Panel>
      <div className="grid grid--2">
        <Panel title={t("read.stats")}>
          <dl className="kv">
            <dt>{t("read.words")}</dt><dd>{formatNumber(r.words, lang, 0)}</dd>
            <dt>{t("read.sentences")}</dt><dd>{formatNumber(r.sentences, lang, 0)}</dd>
            <dt>{t("read.avgSentence")}</dt><dd>{formatNumber(r.avg_sentence_words, lang)} {t("read.wordsUnit")}</dd>
            <dt>{t("read.avgSyll")}</dt><dd>{formatNumber(r.avg_syllables, lang, 2)}</dd>
            <dt>{t("read.longWords")}</dt><dd>{formatNumber(r.long_words_share, lang)} %</dd>
            {r.grade != null && <><dt>{t("read.grade")}</dt><dd>{formatNumber(r.grade, lang)}</dd></>}
            <dt>{t("read.time")}</dt><dd>{t("read.minutes", { n: r.reading_minutes })}</dd>
          </dl>
        </Panel>
        <Panel title={t("read.advice")}>
          <ul className="bullets">
            {r.hints.map((h) => <li key={h.code}>{t(`read.hint.${h.code}`, h.data)}</li>)}
          </ul>
        </Panel>
      </div>
      {r.long_sentences.length > 0 && (
        <Panel title={t("read.longSentences")}>
          <ol className="plain-list plain-list--stack">
            {r.long_sentences.map((s, i) => <li key={i}><span className="badge badge--fair">{t("read.wordsN", { n: s.words })}</span><span>{s.text}</span></li>)}
          </ol>
        </Panel>
      )}
      {r.top_long_words.length > 0 && (
        <Panel title={t("read.hardWords")}>
          <p className="muted small" style={{ marginBottom: "0.6rem" }}>{t("read.hardWordsHint")}</p>
          <p className="row" style={{ gap: "0.4rem" }}>{r.top_long_words.map((w) => <span className="chip" key={w}>{w}</span>)}</p>
        </Panel>
      )}
    </div>
  );
}

export default function Tools() {
  const { t } = useI18n();
  usePageTitle(t("nav.tools"));
  const [query, setQuery] = useQueryState();
  const tab = query.get("tool") || "contrast";
  return (
    <div className="stack-lg">
      <PageHead title={t("tools.title")}>{t("tools.lead")}</PageHead>
      <Panel>
        <Tabs id="tools" label={t("tools.title")} value={tab} onChange={(v) => setQuery({ tool: v === "contrast" ? "" : v })} tabs={[{ id: "contrast", label: t("tools.contrast") }, { id: "readability", label: t("tools.readability") }]} />
        <TabPanel id="tools" tab="contrast" value={tab}><ContrastTool /></TabPanel>
        <TabPanel id="tools" tab="readability" value={tab}><ReadabilityTool /></TabPanel>
      </Panel>
    </div>
  );
}
