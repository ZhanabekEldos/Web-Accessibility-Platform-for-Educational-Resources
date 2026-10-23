import { useId } from "react";
import { scoreBand, formatNumber } from "../format.js";
import { useI18n } from "../i18n/index.jsx";
import { Icon, ImpactIcon } from "./icons.jsx";
import { Link } from "../router.jsx";

export function Button({ variant, size, icon, children, className = "", busy, ...rest }) {
  const cls = ["btn", variant && `btn--${variant}`, size && `btn--${size}`, className].filter(Boolean).join(" ");
  return (
    <button type="button" className={cls} aria-busy={busy || undefined} {...rest} disabled={rest.disabled || busy}>
      {busy ? <span className="spinner" aria-hidden="true" /> : icon ? <Icon name={icon} /> : null}
      {children}
    </button>
  );
}

export function LinkButton({ to, variant, size, icon, children, ...rest }) {
  const cls = ["btn", variant && `btn--${variant}`, size && `btn--${size}`].filter(Boolean).join(" ");
  return <Link to={to} className={cls} {...rest}>{icon && <Icon name={icon} />}{children}</Link>;
}

export function ImpactBadge({ impact }) {
  const { t } = useI18n();
  return <span className={`badge badge--${impact}`}><ImpactIcon impact={impact} />{t(`impact.${impact}`)}</span>;
}

export function LevelBadge({ level }) {
  const { t } = useI18n();
  if (!level) return <span className="badge badge--neutral">{t("level.none")}</span>;
  return <span className="badge badge--accent">WCAG {level}</span>;
}

export function BandBadge({ score }) {
  const { t } = useI18n();
  const band = scoreBand(score);
  return <span className={`badge badge--${band === "none" ? "neutral" : band}`}>{t(`band.${band}`)}</span>;
}

/** Оценка как отметка в тетради: крупная цифра с двойным подчёркиванием. */
export function ScoreMark({ score, size = "md", label }) {
  const { t, lang } = useI18n();
  const band = scoreBand(score);
  const text = score == null ? "—" : formatNumber(score, lang, 0);
  return (
    <span className={`mark mark--${band} mark--${size}`} role="img" aria-label={label || (score == null ? t("score.none") : t("score.aria", { score: text, band: t(`band.${band}`) }))}>
      <span className="mark__value" aria-hidden="true">{text}</span>
      <span className="mark__rule" aria-hidden="true" />
    </span>
  );
}

export function Loading({ label }) {
  const { t } = useI18n();
  return <div className="loading" role="status"><span className="spinner" aria-hidden="true" />{label || t("common.loading")}</div>;
}

export function ErrorNotice({ error, onRetry }) {
  const { t } = useI18n();
  const message = error?.code === "network" ? t("error.network") : error?.message || t("error.generic");
  return (
    <div className="notice notice--error" role="alert">
      <div className="grow"><strong>{t("error.title")}</strong><div>{message}</div></div>
      {onRetry && <Button size="sm" onClick={onRetry}>{t("common.retry")}</Button>}
    </div>
  );
}

export function EmptyState({ title, children, actions }) {
  return (
    <div className="empty">
      <h2>{title}</h2>
      {children && <p>{children}</p>}
      {actions && <div className="row" style={{ justifyContent: "center" }}>{actions}</div>}
    </div>
  );
}

export function PageHead({ title, children, actions, crumbs }) {
  return (
    <header className="page-head">
      <div className="page-head__text">
        {crumbs}
        <h1>{title}</h1>
        {children && <p>{children}</p>}
      </div>
      {actions && <div className="row">{actions}</div>}
    </header>
  );
}

export function Panel({ title, aside, children, className = "", headingLevel = 2 }) {
  const H = `h${headingLevel}`;
  return (
    <section className={`panel ${className}`}>
      {(title || aside) && <div className="panel__head">{title && <H>{title}</H>}{aside}</div>}
      {children}
    </section>
  );
}

/** Поле формы: подпись, подсказка и ошибка связаны с элементом через aria. */
export function Field({ label, hint, error, children, className = "" }) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errId = error ? `${id}-err` : undefined;
  const describedBy = [hintId, errId].filter(Boolean).join(" ") || undefined;
  return (
    <div className={`field ${className}`}>
      <label className="field__label" htmlFor={id}>{label}</label>
      {hint && <span className="field__hint" id={hintId}>{hint}</span>}
      {children({ id, "aria-describedby": describedBy, "aria-invalid": error ? "true" : undefined })}
      {error && <span className="field__error" id={errId}>{error}</span>}
    </div>
  );
}

export function Pagination({ page, pages, total, onPage }) {
  const { t } = useI18n();
  if (pages <= 1) return <p className="muted small" style={{ marginTop: "1rem" }}>{t("common.total", { n: total })}</p>;
  return (
    <nav className="pager" aria-label={t("common.pagination")}>
      <span className="muted small" aria-live="polite">{t("common.pageOf", { page, pages, total })}</span>
      <span className="row">
        <Button size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>{t("common.prev")}</Button>
        <Button size="sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>{t("common.next")}</Button>
      </span>
    </nav>
  );
}

export function SrTable({ caption, head, rows }) {
  return (
    <table className="sr-only">
      <caption>{caption}</caption>
      <thead><tr>{head.map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead>
      <tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody>
    </table>
  );
}

/** Показатель: крупное число над подписью. В DOM сначала dt, потом dd — порядок, который ожидает <dl>. */
export function Stat({ label, value, cls = "" }) {
  return (
    <div className="stat">
      <dt className="stat__label">{label}</dt>
      <dd className={`stat__value num ${cls}`}>{value}</dd>
    </div>
  );
}
