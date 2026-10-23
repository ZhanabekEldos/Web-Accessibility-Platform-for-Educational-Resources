// Настройки отображения: язык, тема, размер текста, анимации. Хранятся в localStorage (если доступно).
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { setApiLang } from "./api.js";

const KEY = "accessedu.prefs";
const DEFAULTS = { lang: "ru", theme: "auto", textSize: "100", motion: "auto" };
const PrefsContext = createContext(null);

function load() {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || "{}");
    const browser = (navigator.language || "ru").slice(0, 2);
    return { ...DEFAULTS, lang: ["ru", "en"].includes(browser) ? browser : "ru", ...saved };
  } catch {
    return { ...DEFAULTS };
  }
}

export function PrefsProvider({ children }) {
  const [prefs, setPrefs] = useState(load);
  useEffect(() => {
    const root = document.documentElement;
    if (prefs.theme === "auto") delete root.dataset.theme; else root.dataset.theme = prefs.theme;
    root.dataset.text = prefs.textSize;
    root.dataset.motion = prefs.motion;
    root.lang = prefs.lang;
    setApiLang(prefs.lang);
    try { localStorage.setItem(KEY, JSON.stringify(prefs)); } catch { /* приватный режим — не критично */ }
  }, [prefs]);
  const update = useCallback((patch) => setPrefs((p) => ({ ...p, ...patch })), []);
  const value = useMemo(() => ({ prefs, update }), [prefs, update]);
  return <PrefsContext.Provider value={value}>{children}</PrefsContext.Provider>;
}

export const usePrefs = () => useContext(PrefsContext);
