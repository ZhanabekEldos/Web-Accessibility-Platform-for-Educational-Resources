import { createContext, useCallback, useContext, useEffect, useId, useRef, useState } from "react";
import { useI18n } from "../i18n/index.jsx";
import { Button } from "./ui.jsx";

/** Модальное окно на нативном <dialog>: фокус-ловушка, Esc и возврат фокуса обеспечивает браузер. */
export function Dialog({ open, onClose, title, children, wide }) {
  const ref = useRef(null);
  const titleId = useId();
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);
  return (
    <dialog ref={ref} className="dialog" style={wide ? { width: "min(52rem, calc(100vw - 2rem))" } : undefined} aria-labelledby={open ? titleId : undefined} onClose={onClose}
      onClick={(e) => { if (e.target === ref.current) onClose(); }}>
      {open && (
        <div className="dialog__form">
          <h2 id={titleId}>{title}</h2>
          {children}
        </div>
      )}
    </dialog>
  );
}

const ConfirmContext = createContext(null);

export function ConfirmProvider({ children }) {
  const { t } = useI18n();
  const [state, setState] = useState(null);
  const confirm = useCallback((options) => new Promise((resolve) => setState({ ...options, resolve })), []);
  const settle = (value) => { state?.resolve(value); setState(null); };
  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      <Dialog open={!!state} onClose={() => settle(false)} title={state?.title || ""}>
        {state?.body && <p>{state.body}</p>}
        <div className="dialog__actions">
          <Button onClick={() => settle(false)}>{t("common.cancel")}</Button>
          <Button variant={state?.danger ? "danger" : "primary"} onClick={() => settle(true)}>{state?.confirmLabel || t("common.confirm")}</Button>
        </div>
      </Dialog>
    </ConfirmContext.Provider>
  );
}

export const useConfirm = () => useContext(ConfirmContext);
