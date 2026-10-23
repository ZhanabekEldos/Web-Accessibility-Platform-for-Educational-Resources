import { useI18n, LANGUAGES } from "../i18n/index.jsx";
import { usePrefs } from "../prefs.jsx";
import { Dialog } from "./Dialog.jsx";
import { Button, Field } from "./ui.jsx";

/** Настройки отображения — часть самого продукта о доступности. */
export function SettingsDialog({ open, onClose }) {
  const { t } = useI18n();
  const { prefs, update } = usePrefs();
  return (
    <Dialog open={open} onClose={onClose} title={t("settings.title")}>
      <div className="stack">
        <Field label={t("settings.language")}>{(p) => <select {...p} className="select" value={prefs.lang} onChange={(e) => update({ lang: e.target.value })}>{LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}</select>}</Field>
        <Field label={t("settings.theme")}>{(p) => (
          <select {...p} className="select" value={prefs.theme} onChange={(e) => update({ theme: e.target.value })}>
            {["auto", "light", "dark", "contrast"].map((v) => <option key={v} value={v}>{t(`settings.theme.${v}`)}</option>)}
          </select>)}</Field>
        <Field label={t("settings.textSize")} hint={t("settings.textSizeHint")}>{(p) => (
          <select {...p} className="select" value={prefs.textSize} onChange={(e) => update({ textSize: e.target.value })}>
            {["100", "115", "130"].map((v) => <option key={v} value={v}>{v}%</option>)}
          </select>)}</Field>
        <Field label={t("settings.motion")}>{(p) => (
          <select {...p} className="select" value={prefs.motion} onChange={(e) => update({ motion: e.target.value })}>
            {["auto", "reduce", "allow"].map((v) => <option key={v} value={v}>{t(`settings.motion.${v}`)}</option>)}
          </select>)}</Field>
        <div className="dialog__actions"><Button variant="primary" onClick={onClose}>{t("common.done")}</Button></div>
      </div>
    </Dialog>
  );
}
