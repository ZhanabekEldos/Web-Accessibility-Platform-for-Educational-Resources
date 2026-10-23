// Минимальный роутер на History API: достаточно для приложения и без внешних зависимостей.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

const RouterContext = createContext(null);

function parse(pattern, path) {
  const keys = [];
  const re = new RegExp("^" + pattern.replace(/:([a-z]+)/gi, (_, k) => (keys.push(k), "([^/]+)")) + "/?$");
  const m = re.exec(path);
  return m ? Object.fromEntries(keys.map((k, i) => [k, decodeURIComponent(m[i + 1])])) : null;
}

export function Router({ routes, children }) {
  const [loc, setLoc] = useState(() => ({ path: window.location.pathname, search: window.location.search }));
  useEffect(() => {
    const onPop = () => setLoc({ path: window.location.pathname, search: window.location.search });
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  const navigate = useCallback((to, { replace = false } = {}) => {
    const url = new URL(to, window.location.origin);
    window.history[replace ? "replaceState" : "pushState"](null, "", url.pathname + url.search);
    setLoc({ path: url.pathname, search: url.search });
  }, []);
  const value = useMemo(() => {
    let match = null;
    for (const route of routes) {
      const params = parse(route.path, loc.path);
      if (params) { match = { route, params }; break; }
    }
    return { ...loc, query: new URLSearchParams(loc.search), match, navigate };
  }, [loc, routes, navigate]);
  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>;
}

export const useRouter = () => useContext(RouterContext);

export function Link({ to, children, onClick, ...rest }) {
  const { navigate } = useRouter();
  return (
    <a
      href={to}
      {...rest}
      onClick={(e) => {
        onClick?.(e);
        if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || rest.target === "_blank") return;
        e.preventDefault();
        navigate(to);
      }}
    >
      {children}
    </a>
  );
}

/** Обновляет query-параметры текущей страницы без перезагрузки. */
export function useQueryState() {
  const { query, path, navigate } = useRouter();
  const set = useCallback((patch, opts) => {
    const next = new URLSearchParams(window.location.search);
    for (const [k, v] of Object.entries(patch)) (v === "" || v == null ? next.delete(k) : next.set(k, v));
    const qs = next.toString();
    navigate(path + (qs ? "?" + qs : ""), { replace: true, ...opts });
  }, [path, navigate]);
  return [query, set];
}
