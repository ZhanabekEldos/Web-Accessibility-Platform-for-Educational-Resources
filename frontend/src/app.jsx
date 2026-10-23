import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Icon } from "./components/icons.jsx";
import { SettingsDialog } from "./components/Settings.jsx";
import { Button, EmptyState, LinkButton, Loading } from "./components/ui.jsx";
import { usePageTitle, useUnreadEvents } from "./hooks.js";
import { useI18n } from "./i18n/index.jsx";
import { Link, Router, useRouter } from "./router.jsx";

import Dashboard from "./pages/Dashboard.jsx";
import Resources from "./pages/Resources.jsx";
import ResourceDetail from "./pages/ResourceDetail.jsx";
import Check from "./pages/Check.jsx";
import Collections from "./pages/Collections.jsx";
import Notifications from "./pages/Notifications.jsx";
const Rules = lazy(() => import("./pages/Rules.jsx"));
const Tools = lazy(() => import("./pages/Tools.jsx"));
const AcademyList = lazy(() => import("./pages/Academy.jsx").then((m) => ({ default: m.AcademyList })));
const Lesson = lazy(() => import("./pages/Academy.jsx").then((m) => ({ default: m.Lesson })));
const lazyPage = (node) => <Suspense fallback={<Loading />}>{node}</Suspense>;

const ROUTES = [
  { path: "/", name: "dashboard", render: () => <Dashboard /> },
  { path: "/resources", name: "resources", render: () => <Resources /> },
  { path: "/resources/:id", name: "resources", render: ({ id }) => <ResourceDetail key={id} id={id} /> },
  { path: "/check", name: "check", render: () => <Check /> },
  { path: "/collections", name: "collections", render: () => <Collections /> },
  { path: "/rules", name: "rules", render: () => lazyPage(<Rules />) },
  { path: "/tools", name: "tools", render: () => lazyPage(<Tools />) },
  { path: "/academy", name: "academy", render: () => lazyPage(<AcademyList />) },
  { path: "/academy/:id", name: "academy", render: ({ id }) => lazyPage(<Lesson key={id} id={id} />) },
  { path: "/notifications", name: "notifications", render: () => <Notifications /> },
];
const NAV = [
  { to: "/", name: "dashboard", icon: "dashboard" },
  { to: "/resources", name: "resources", icon: "folder" },
  { to: "/check", name: "check", icon: "check" },
  { to: "/collections", name: "collections", icon: "layers" },
  { to: "/tools", name: "tools", icon: "tools" },
  { to: "/academy", name: "academy", icon: "cap" },
  { to: "/rules", name: "rules", icon: "book" },
  { to: "/notifications", name: "notifications", icon: "bell", badge: true },
];

function NotFound() {
  const { t } = useI18n();
  usePageTitle(t("notFound.title"));
  return <EmptyState title={t("notFound.title")} actions={<LinkButton to="/" variant="primary">{t("notFound.home")}</LinkButton>}>{t("notFound.text")}</EmptyState>;
}

function Shell() {
  const { t } = useI18n();
  const { match, path } = useRouter();
  const [settings, setSettings] = useState(false);
  const main = useRef(null);
  const first = useRef(true);
  const active = match?.route.name;
  const unread = useUnreadEvents(path);

  // После перехода переносим фокус в основное содержимое, чтобы скринридер озвучил новую страницу.
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    main.current?.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }, [path]);

  return (
    <>
      <a className="skip-link" href="#main" onClick={(e) => { e.preventDefault(); main.current?.focus(); }}>{t("nav.skip")}</a>
      <div className="shell">
        <aside className="rail">
          <Link to="/" className="brand" aria-label={t("brand.home")}>
            <span className="brand__glyph" aria-hidden="true">A</span>
            <span><span className="brand__name">AccessEdu</span><span className="brand__sub">{t("brand.tagline")}</span></span>
          </Link>
          <nav className="nav" aria-label={t("nav.main")}>
            {NAV.map((n) => (
              <Link key={n.to} to={n.to} className="nav__link" aria-current={active === n.name ? "page" : undefined}>
                <Icon name={n.icon} className="nav__icon" />{t(`nav.${n.name}`)}
                {n.badge && unread > 0 && <span className="nav__count">{unread}<span className="sr-only"> {t("events.unreadSr")}</span></span>}
              </Link>
            ))}
          </nav>
          <div className="rail__foot"><Button icon="settings" onClick={() => setSettings(true)}>{t("settings.open")}</Button></div>
        </aside>
        <main id="main" ref={main} tabIndex={-1} className="content">
          {match ? match.route.render(match.params) : <NotFound />}
        </main>
      </div>
      <SettingsDialog open={settings} onClose={() => setSettings(false)} />
    </>
  );
}

export default function App() {
  const routes = useMemo(() => ROUTES, []);
  return <Router routes={routes}><Shell /></Router>;
}
