import { createContext, useCallback, useContext, useRef, useState } from "react";
import { useI18n } from "../i18n/index.jsx";

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const { t } = useI18n();
  const [items, setItems] = useState([]);
  const seq = useRef(0);
  const dismiss = useCallback((id) => setItems((list) => list.filter((i) => i.id !== id)), []);
  const push = useCallback((message, { type = "info", timeout = 8000 } = {}) => {
    const id = ++seq.current;
    setItems((list) => [...list.slice(-3), { id, message, type }]);
    if (timeout) setTimeout(() => dismiss(id), timeout);
  }, [dismiss]);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toasts">
        <div role="status" aria-live="polite">
          {items.filter((i) => i.type !== "error").map((i) => <Toast key={i.id} item={i} onClose={dismiss} label={t("common.close")} />)}
        </div>
        <div role="alert">
          {items.filter((i) => i.type === "error").map((i) => <Toast key={i.id} item={i} onClose={dismiss} label={t("common.close")} />)}
        </div>
      </div>
    </ToastContext.Provider>
  );
}

function Toast({ item, onClose, label }) {
  return (
    <div className={`toast ${item.type === "error" ? "toast--error" : ""}`}>
      <span>{item.message}</span>
      <button type="button" onClick={() => onClose(item.id)}>{label}</button>
    </div>
  );
}

export const useToast = () => useContext(ToastContext);
