import { useRef } from "react";

/** Вкладки по шаблону WAI-ARIA: стрелки, Home/End, «блуждающий» tabindex. */
export function Tabs({ id, label, tabs, value, onChange }) {
  const refs = useRef({});
  const move = (index) => {
    const next = tabs[(index + tabs.length) % tabs.length];
    onChange(next.id);
    refs.current[next.id]?.focus();
  };
  const onKeyDown = (e, index) => {
    if (e.key === "ArrowRight") { e.preventDefault(); move(index + 1); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); move(index - 1); }
    else if (e.key === "Home") { e.preventDefault(); move(0); }
    else if (e.key === "End") { e.preventDefault(); move(tabs.length - 1); }
  };
  return (
    <div className="tabs" role="tablist" aria-label={label}>
      {tabs.map((tab, i) => (
        <button
          key={tab.id} ref={(el) => { refs.current[tab.id] = el; }} type="button" role="tab" className="tab"
          id={`${id}-tab-${tab.id}`} aria-selected={value === tab.id} aria-controls={`${id}-panel-${tab.id}`}
          tabIndex={value === tab.id ? 0 : -1} onClick={() => onChange(tab.id)} onKeyDown={(e) => onKeyDown(e, i)}
        >
          {tab.label}
          {tab.count != null && <span className="badge badge--neutral">{tab.count}</span>}
        </button>
      ))}
    </div>
  );
}

/** Панель всегда есть в DOM (чтобы aria-controls у вкладки был валиден), но содержимое монтируется только у активной. */
export function TabPanel({ id, tab, value, children }) {
  const active = tab === value;
  return (
    <div role="tabpanel" id={`${id}-panel-${tab}`} aria-labelledby={`${id}-tab-${tab}`} tabIndex={active ? 0 : undefined} hidden={!active}>
      {active ? children : null}
    </div>
  );
}
