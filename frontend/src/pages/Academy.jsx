import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { Button, ErrorNotice, LinkButton, Loading, PageHead, Panel } from "../components/ui.jsx";
import { useApi, usePageTitle } from "../hooks.js";
import { useI18n } from "../i18n/index.jsx";
import { Link } from "../router.jsx";

export function AcademyList() {
  const { t } = useI18n();
  usePageTitle(t("nav.academy"));
  const list = useApi("/academy");
  const head = <PageHead title={t("academy.title")}>{t("academy.lead")}</PageHead>;
  if (list.error) return <>{head}<ErrorNotice error={list.error} onRetry={list.reload} /></>;
  if (!list.data) return <>{head}<Loading /></>;
  const { items, completed, total } = list.data;
  return (
    <div className="stack-lg">
      {head}
      <Panel>
        <div className="progress">
          <div className="row-between"><strong>{t("academy.progress", { done: completed, total })}</strong><span className="muted small">{Math.round((completed / total) * 100)} %</span></div>
          <div className="meter" role="progressbar" aria-label={t("academy.progressLabel")} aria-valuemin={0} aria-valuemax={total} aria-valuenow={completed}>
            <span className="meter__fill meter__fill--good" style={{ width: `${(completed / total) * 100}%` }} />
          </div>
        </div>
      </Panel>
      <ol className="lesson-grid">
        {items.map((l, i) => (
          <li key={l.id} className="lesson-card">
            <span className="lesson-card__n" aria-hidden="true">{i + 1}</span>
            <div className="stack" style={{ gap: "0.5rem" }}>
              <h2 className="lesson-card__title"><Link to={`/academy/${l.id}`} className="rowlink">{l.title}</Link></h2>
              <p className="muted">{l.summary}</p>
              <p className="row small" style={{ gap: "0.5rem" }}>
                <span className="badge badge--neutral">{t("academy.minutes", { n: l.minutes })}</span>
                <span className="badge badge--neutral">{t("academy.questions", { n: l.questions })}</span>
                {l.progress?.completed ? <span className="badge badge--good">✓ {t("academy.done", { score: l.progress.best_score, total: l.progress.total })}</span>
                  : l.progress ? <span className="badge badge--fair">{t("academy.tried", { score: l.progress.best_score, total: l.progress.total })}</span> : null}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

function Quiz({ lesson, onDone }) {
  const { t } = useI18n();
  const [answers, setAnswers] = useState({});
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const heading = useRef(null);
  useEffect(() => { if (result) heading.current?.focus(); }, [result]);

  const submit = async (e) => {
    e.preventDefault();
    if (lesson.quiz.some((q) => answers[q.id] == null)) { setError(t("academy.answerAll")); return; }
    setError(""); setBusy(true);
    try { const res = await api.post(`/academy/${lesson.id}/quiz`, { answers: lesson.quiz.map((q) => answers[q.id]) }); setResult(res); onDone(); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  };
  const retry = () => { setResult(null); setAnswers({}); };
  const byId = Object.fromEntries((result?.results || []).map((r) => [r.id, r]));

  return (
    <form className="stack-lg" onSubmit={submit} noValidate aria-labelledby="quiz-title">
      <h2 id="quiz-title">{t("academy.quiz")}</h2>
      {result && (
        <div className={`notice ${result.passed ? "notice--ok" : ""}`} role="status">
          <div className="grow">
            <h3 ref={heading} tabIndex={-1} style={{ outline: "none" }}>{t(result.passed ? "academy.passed" : "academy.notPassed", { score: result.score, total: result.total })}</h3>
            <p>{t(result.passed ? "academy.passedText" : "academy.notPassedText")}</p>
          </div>
        </div>
      )}
      {lesson.quiz.map((q, qi) => {
        const r = byId[q.id];
        return (
          <fieldset key={q.id} className={`question${r ? (r.correct ? " is-correct" : " is-wrong") : ""}`} disabled={!!result}>
            <legend><span className="muted">{qi + 1}.</span> {q.question}</legend>
            <div className="options">
              {q.options.map((o, oi) => {
                const chosen = answers[q.id] === oi;
                const isAnswer = r && r.answer === oi;
                return (
                  <label key={oi} className={`option${chosen ? " is-chosen" : ""}${isAnswer ? " is-answer" : ""}`}>
                    <input type="radio" name={`q${q.id}`} checked={chosen} onChange={() => setAnswers({ ...answers, [q.id]: oi })} />
                    <span>{o}{isAnswer && <strong className="option__flag"> — {t("academy.correctAnswer")}</strong>}{r && chosen && !isAnswer && <strong className="option__flag option__flag--bad"> — {t("academy.yourAnswer")}</strong>}</span>
                  </label>
                );
              })}
            </div>
            {r && <p className="question__explain"><strong>{t(r.correct ? "academy.correct" : "academy.wrong")}.</strong> {r.explain}</p>}
          </fieldset>
        );
      })}
      {error && <p className="field__error" role="alert">{error}</p>}
      <div className="row">
        {!result ? <Button variant="primary" type="submit" icon="check" busy={busy}>{t("academy.check")}</Button> : <Button onClick={retry} icon="refresh">{t("academy.retry")}</Button>}
      </div>
    </form>
  );
}

export function Lesson({ id }) {
  const { t } = useI18n();
  const lesson = useApi(`/academy/${id}`);
  usePageTitle(lesson.data?.title);
  if (lesson.error) return <ErrorNotice error={lesson.error} onRetry={lesson.reload} />;
  if (!lesson.data) return <Loading />;
  const l = lesson.data;
  return (
    <div className="stack-lg">
      <PageHead
        title={l.title}
        crumbs={<nav className="crumbs" aria-label={t("common.breadcrumbs")}><Link to="/academy">{t("nav.academy")}</Link></nav>}
      >{l.summary}</PageHead>
      <p className="row small" style={{ gap: "0.5rem" }}>
        <span className="badge badge--neutral">{t("academy.minutes", { n: l.minutes })}</span>
        {l.wcag.map((c) => <a key={c.id} className="chip" href={c.url} target="_blank" rel="noreferrer noopener">WCAG {c.id}<span className="sr-only"> ({t("common.newTab")})</span></a>)}
      </p>
      <article className="panel lesson stack-lg">
        {l.sections.map((s, i) => (
          <section key={i} className="stack">
            <h2>{s.heading}</h2>
            {s.paragraphs?.map((p, j) => <p key={j}>{p}</p>)}
            {s.points && <ul className="bullets">{s.points.map((p, j) => <li key={j}>{p}</li>)}</ul>}
          </section>
        ))}
        {l.example && (
          <section className="stack" aria-label={t("academy.example")}>
            <h2>{t("academy.example")}</h2>
            <div className="example">
              <figure className="bad" style={{ margin: 0 }}><figcaption>✕ {t("rules.bad")}</figcaption><pre className="code"><code>{l.example.bad}</code></pre></figure>
              <figure className="good" style={{ margin: 0 }}><figcaption>✓ {t("rules.good")}</figcaption><pre className="code"><code>{l.example.good}</code></pre></figure>
            </div>
            <p className="muted small">{l.example.caption}</p>
          </section>
        )}
      </article>
      <Panel><Quiz key={id} lesson={l} onDone={lesson.reload} /></Panel>
      <nav className="row-between" aria-label={t("academy.lessonNav")}>
        {l.prev ? <LinkButton to={`/academy/${l.prev}`}>← {t("academy.prev")}</LinkButton> : <span />}
        {l.next ? <LinkButton to={`/academy/${l.next}`} variant="primary">{t("academy.next")} →</LinkButton> : <LinkButton to="/academy">{t("academy.all")}</LinkButton>}
      </nav>
    </div>
  );
}
