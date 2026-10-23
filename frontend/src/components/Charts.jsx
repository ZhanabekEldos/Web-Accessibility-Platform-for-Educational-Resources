import { useI18n } from "../i18n/index.jsx";
import { formatDate, formatNumber } from "../format.js";
import { SrTable } from "./ui.jsx";

/** Динамика средней оценки. Точки доступны с клавиатуры, таблица-дубликат — для скринридеров. */
export function TrendChart({ data }) {
  const { t, lang } = useI18n();
  if (!data?.length) return <p className="muted">{t("chart.noData")}</p>;
  const W = 640, H = 220, L = 34, R = 12, T = 12, B = 28;
  const x = (i) => (data.length === 1 ? (L + W - R) / 2 : L + (i * (W - L - R)) / (data.length - 1));
  const y = (v) => T + ((100 - v) * (H - T - B)) / 100;
  const points = data.map((d, i) => [x(i), y(d.avg_score), d]);
  const line = points.map(([px, py], i) => `${i ? "L" : "M"}${px.toFixed(1)} ${py.toFixed(1)}`).join(" ");
  const area = `${line} L${points.at(-1)[0].toFixed(1)} ${y(0)} L${points[0][0].toFixed(1)} ${y(0)} Z`;
  const first = data[0], last = data.at(-1);
  const summary = t("chart.trendSummary", { from: formatNumber(first.avg_score, lang), to: formatNumber(last.avg_score, lang), start: formatDate(first.day, lang), end: formatDate(last.day, lang) });
  const labelIdx = [...new Set([0, Math.floor((data.length - 1) / 2), data.length - 1])];
  return (
    <figure style={{ margin: 0 }}>
      <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="group" aria-label={summary}>
        {[0, 25, 50, 75, 100].map((v) => (
          <g key={v}>
            <line className="grid-line" x1={L} x2={W - R} y1={y(v)} y2={y(v)} />
            <text x={L - 6} y={y(v) + 4} textAnchor="end">{v}</text>
          </g>
        ))}
        {data.length > 1 && <path className="area" d={area} />}
        {data.length > 1 && <path className="line" d={line} />}
        {points.map(([px, py, d], i) => (
          <circle key={d.day} className="dot" cx={px} cy={py} r="5" tabIndex={0} role="img"
            aria-label={t("chart.point", { date: formatDate(d.day, lang), score: formatNumber(d.avg_score, lang), n: d.scans })}>
            <title>{`${formatDate(d.day, lang)}: ${formatNumber(d.avg_score, lang)}`}</title>
          </circle>
        ))}
        {labelIdx.map((i) => (
          <text key={i} x={x(i)} y={H - 6} textAnchor={i === 0 && data.length > 1 ? "start" : i === data.length - 1 && data.length > 1 ? "end" : "middle"}>{formatDate(data[i].day, lang)}</text>
        ))}
      </svg>
      <SrTable caption={t("chart.trendTitle")} head={[t("chart.date"), t("chart.avg"), t("chart.scans")]}
        rows={data.map((d) => [formatDate(d.day, lang), formatNumber(d.avg_score, lang), d.scans])} />
    </figure>
  );
}

/** Составная полоса с подписанной легендой (значения дублируются текстом). */
export function Distribution({ items, label }) {
  const total = items.reduce((n, i) => n + i.value, 0);
  return (
    <div>
      <div className="segbar" role="img" aria-label={`${label}: ${items.map((i) => `${i.label} ${i.value}`).join(", ")}`}>
        {items.filter((i) => i.value > 0).map((i) => <span key={i.key} className={`seg--${i.cls}`} style={{ flexGrow: i.value }} />)}
        {total === 0 && <span className="seg--none" style={{ flexGrow: 1 }} />}
      </div>
      <ul className="legend">
        {items.map((i) => <li key={i.key}><i className={`seg--${i.cls}`} aria-hidden="true" /><span>{i.label}: <strong className="num">{i.value}</strong></span></li>)}
      </ul>
    </div>
  );
}

export function BarList({ items, max = 100, format = (v) => v }) {
  return (
    <div className="bars">
      {items.map((i) => (
        <div className="bar" key={i.key}>
          <div className="bar__head"><span>{i.label}</span><strong className="num">{i.value == null ? "—" : format(i.value)}</strong></div>
          <div className="bar__track" role="presentation"><div className={`bar__fill ${i.cls ? `bar__fill--${i.cls}` : ""}`} style={{ width: `${Math.max(0, Math.min(100, ((i.value ?? 0) / max) * 100))}%` }} /></div>
        </div>
      ))}
    </div>
  );
}
