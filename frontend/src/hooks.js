import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";

/** Загрузка данных: { data, error, loading, reload }. Отменяет устаревшие запросы. */
export function useApi(path, params, { skip = false } = {}) {
  const [state, setState] = useState({ data: null, error: null, loading: !skip });
  const key = path + JSON.stringify(params || {});
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (skip || !path) { setState({ data: null, error: null, loading: false }); return; }
    const ctrl = new AbortController();
    setState((s) => ({ ...s, loading: true, error: null }));
    api.get(path, params, ctrl.signal)
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((error) => { if (error.name !== "AbortError") setState({ data: null, error, loading: false }); });
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, skip, tick]);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, reload };
}

export function useDebounced(value, delay = 300) {
  const [v, setV] = useState(value);
  useEffect(() => { const id = setTimeout(() => setV(value), delay); return () => clearTimeout(id); }, [value, delay]);
  return v;
}

export function usePrevious(value) {
  const ref = useRef();
  useEffect(() => { ref.current = value; });
  return ref.current;
}

/** Заголовок вкладки браузера; страница с понятным <title> — это и WCAG 2.4.2. */
export function usePageTitle(title) {
  useEffect(() => {
    if (title) document.title = `${title} — AccessEdu`;
  }, [title]);
}

/** Сообщает всем подписчикам, что уведомления изменились (прочитаны, добавлены). */
export const notifyEventsChanged = () => window.dispatchEvent(new Event("accessedu:events"));

/** Число непрочитанных уведомлений: обновляется при переходах, по таймеру и по событию. */
export function useUnreadEvents(dep) {
  const [count, setCount] = useState(0);
  const refresh = useCallback(() => { api.get("/events/unread-count").then((d) => setCount(d.unread)).catch(() => {}); }, []);
  useEffect(() => { refresh(); }, [refresh, dep]);
  useEffect(() => {
    const id = setInterval(refresh, 60000);
    window.addEventListener("accessedu:events", refresh);
    return () => { clearInterval(id); window.removeEventListener("accessedu:events", refresh); };
  }, [refresh]);
  return count;
}

/** Копирование в буфер обмена с запасным вариантом; возвращает true при успехе. */
export async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return true; } catch { return false; }
}
