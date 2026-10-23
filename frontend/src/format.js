export const scoreBand = (score) => (score == null ? "none" : score >= 90 ? "good" : score >= 70 ? "fair" : "poor");

export function formatDate(iso, lang, withTime = false) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat(lang, withTime ? { dateStyle: "medium", timeStyle: "short" } : { dateStyle: "medium" }).format(d);
}

export function formatNumber(n, lang, digits = 1) {
  if (n == null) return "—";
  return new Intl.NumberFormat(lang, { maximumFractionDigits: digits }).format(n);
}

export function relativeDays(iso, lang) {
  if (!iso) return "—";
  const days = Math.round((new Date(iso).getTime() - Date.now()) / 86400000);
  return new Intl.RelativeTimeFormat(lang, { numeric: "auto" }).format(days, "day");
}
