import { useEffect, useRef, useState } from "react";
import { Icon } from "./icons.jsx";

/** Выпадающее меню-«раскрытие»: кнопка с aria-expanded и список ссылок/кнопок. Esc и клик снаружи закрывают. */
export function Menu({ label, icon, children }) {
  const [open, setOpen] = useState(false);
  const root = useRef(null);
  const button = useRef(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (e) => { if (!root.current?.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === "Escape") { setOpen(false); button.current?.focus(); } };
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("pointerdown", onDown); document.removeEventListener("keydown", onKey); };
  }, [open]);
  return (
    <div className="menu" ref={root}>
      <button ref={button} type="button" className="btn" aria-expanded={open} aria-haspopup="true" onClick={() => setOpen((o) => !o)}>
        {icon && <Icon name={icon} />}{label}
      </button>
      {open && <div className="menu__list" onClick={() => setOpen(false)}>{children}</div>}
    </div>
  );
}
