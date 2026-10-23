import { useState } from "react";
import { api } from "../api.js";
import { useConfirm } from "../components/Dialog.jsx";
import { useToast } from "../components/Toast.jsx";
import { Button, EmptyState, ErrorNotice, Loading, PageHead, Pagination } from "../components/ui.jsx";
import { formatDate, formatNumber } from "../format.js";
import { notifyEventsChanged, useApi, usePageTitle } from "../hooks.js";
import { useI18n } from "../i18n/index.jsx";
import { Link } from "../router.jsx";

const ICON = { warning: "▲", success: "✓", info: "●" };

function Message({ e }) {
  const { t, lang } = useI18n();
  const d = e.data || {};
  const params = {
    from: formatNumber(d.from ?? 0, lang, 0), to: formatNumber(d.to ?? 0, lang, 0), n: d.count ?? 0, error: d.error || "",
    fromLevel: d.from || t("level.none"), toLevel: d.to || t("level.none"),
  };
  return <>{t(`event.${e.type}`, params)}</>;
}

export default function Notifications() {
  const { t, lang } = useI18n();
  const toast = useToast();
  const confirm = useConfirm();
  usePageTitle(t("nav.notifications"));
  const [page, setPage] = useState(1);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const list = useApi("/events", { page, per_page: 20, unread: unreadOnly ? 1 : "" });

  const markAll = async () => { await api.post("/events/read", {}); notifyEventsChanged(); list.reload(); };
  const markOne = async (id) => { await api.post("/events/read", { ids: [id] }); notifyEventsChanged(); list.reload(); };
  const clear = async () => {
    if (!(await confirm({ title: t("events.clearTitle"), body: t("events.clearBody"), confirmLabel: t("events.clear"), danger: true }))) return;
    try { await api.del("/events"); notifyEventsChanged(); toast(t("events.cleared")); setPage(1); list.reload(); } catch (e) { toast(e.message, { type: "error" }); }
  };

  const head = (
    <PageHead title={t("events.title")} actions={<>
      <label className="check"><input type="checkbox" checked={unreadOnly} onChange={(e) => { setUnreadOnly(e.target.checked); setPage(1); }} />{t("events.unreadOnly")}</label>
      <Button onClick={markAll} disabled={!list.data?.unread}>{t("events.markAll")}</Button>
      <Button variant="danger" icon="trash" onClick={clear} disabled={!list.data?.total && !unreadOnly}>{t("events.clear")}</Button>
    </>}>{t("events.lead")}</PageHead>
  );
  if (list.error) return <>{head}<ErrorNotice error={list.error} onRetry={list.reload} /></>;
  if (!list.data) return <>{head}<Loading /></>;
  return (
    <div className="stack-lg">
      {head}
      {list.data.items.length === 0 ? (
        <EmptyState title={t("events.emptyTitle")}>{t("events.emptyText")}</EmptyState>
      ) : (
        <>
          <ul className="events" aria-label={t("events.title")}>
            {list.data.items.map((e) => (
              <li key={e.id} className={`event event--${e.severity}${e.read ? " is-read" : ""}`}>
                <span className="event__icon" aria-hidden="true">{ICON[e.severity] || ICON.info}</span>
                <div className="event__body">
                  <p>
                    {!e.read && <span className="badge badge--accent">{t("events.new")}</span>}{" "}
                    {e.resource_id ? <Link to={`/resources/${e.resource_id}${e.scan_id ? `?scan=${e.scan_id}` : ""}`}><strong>{e.resource_title}</strong></Link> : null}
                    {" — "}<Message e={e} />
                  </p>
                  <p className="muted small"><time dateTime={e.created_at}>{formatDate(e.created_at, lang, true)}</time></p>
                </div>
                {!e.read && <Button size="sm" onClick={() => markOne(e.id)}>{t("events.markRead")}<span className="sr-only">: {e.resource_title}</span></Button>}
              </li>
            ))}
          </ul>
          <Pagination page={list.data.page} pages={list.data.pages} total={list.data.total} onPage={setPage} />
        </>
      )}
    </div>
  );
}
