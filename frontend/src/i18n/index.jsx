import { createContext, useCallback, useContext, useMemo } from "react";
import { usePrefs } from "../prefs.jsx";
import en from "./en.js";
import ru from "./ru.js";

const DICTS = { ru, en };
export const LANGUAGES = [
  { code: "ru", label: "Русский" },
  { code: "en", label: "English" },
];
const I18nContext = createContext(null);

function lookup(dict, key) {
  return dict[key]; // плоский словарь: ключи вида "nav.dashboard"
}

export function I18nProvider({ children }) {
  const { prefs } = usePrefs();
  const lang = prefs.lang in DICTS ? prefs.lang : "ru";
  const rules = useMemo(() => new Intl.PluralRules(lang), [lang]);

  const t = useCallback((key, params = {}) => {
    let value = lookup(DICTS[lang], key) ?? lookup(DICTS.en, key);
    if (value == null) return key;
    // Множественное число: значение — объект { one, few, many, other } и params.n
    if (typeof value === "object") value = value[rules.select(params.n ?? 0)] ?? value.other;
    return String(value).replace(/\{(\w+)\}/g, (_, name) => (params[name] ?? `{${name}}`));
  }, [lang, rules]);

  const value = useMemo(() => ({ t, lang }), [t, lang]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export const useI18n = () => useContext(I18nContext);
