// Набор штриховых иконок (24×24). Декоративные: скрыты от скринридеров, смысл всегда дублируется текстом.
const PATHS = {
  dashboard: "M4 13h6V4H4v9Zm0 7h6v-5H4v5Zm10 0h6v-9h-6v9Zm0-16v5h6V4h-6Z",
  folder: "M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z",
  check: "M12 3 4 6v6c0 4.5 3.2 8 8 9 4.8-1 8-4.5 8-9V6l-8-3Zm-3 9 2 2 4-4",
  book: "M5 4h10a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3V4Zm3 12h10M8 8h6",
  layers: "m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5m-18 4 9 5 9-5",
  settings: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm7.4-3a7.4 7.4 0 0 0-.1-1.2l2-1.6-2-3.4-2.4 1a7 7 0 0 0-2-1.2L14.5 3h-4l-.4 2.6a7 7 0 0 0-2 1.2l-2.4-1-2 3.4 2 1.6a7.4 7.4 0 0 0 0 2.4l-2 1.6 2 3.4 2.4-1a7 7 0 0 0 2 1.2l.4 2.6h4l.4-2.6a7 7 0 0 0 2-1.2l2.4 1 2-3.4-2-1.6c.1-.4.1-.8.1-1.2Z",
  search: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Zm5-2 5 5",
  plus: "M12 5v14M5 12h14",
  refresh: "M20 11a8 8 0 0 0-14.9-3M4 4v4h4M4 13a8 8 0 0 0 14.9 3M20 20v-4h-4",
  download: "M12 4v11m0 0-4-4m4 4 4-4M5 20h14",
  trash: "M4 7h16M10 11v6m4-6v6M6 7l1 13h10l1-13M9 7V4h6v3",
  edit: "M4 20h4L19 9l-4-4L4 16v4Zm9-13 4 4",
  chevron: "m9 6 6 6-6 6",
  external: "M14 4h6v6m0-6-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5",
  close: "M6 6l12 12M18 6 6 18",
  play: "M8 5v14l11-7L8 5Z",
  history: "M4 12a8 8 0 1 0 2.3-5.6M4 4v4h4M12 8v4l3 2",
  list: "M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01",
  bell: "M6 9a6 6 0 1 1 12 0c0 5 2 6 2 7H4c0-1 2-2 2-7Zm4 10a2 2 0 0 0 4 0",
  tools: "M14.7 6.3a4 4 0 0 0-5.4 5.2L3 17.8 6.2 21l6.3-6.3a4 4 0 0 0 5.2-5.4l-2.5 2.5-2.4-.6-.6-2.4 2.5-2.5Z",
  cap: "m12 4 10 5-10 5L2 9l10-5Zm-6 7.5V16c0 1.5 3 3 6 3s6-1.5 6-3v-4.5",
  globe: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm-9-9h18M12 3c2.5 2.5 3.5 5.5 3.5 9S14.5 18.5 12 21c-2.5-2.5-3.5-5.5-3.5-9S9.5 5.5 12 3Z",
  clipboard: "M9 4h6v3H9V4Zm-2 2H5v15h14V6h-2M9 14l2 2 4-4",
  file: "M7 3h7l4 4v14H7V3Zm7 0v4h4M10 12h5m-5 4h5",
  copy: "M9 9h10v11H9V9Zm-4 6V4h10",
  swap: "M7 4 3 8l4 4M3 8h14M17 20l4-4-4-4m4 4H7",
  clock: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-13v5l3 2",
  sparkles: "M12 3v4m0 10v4M3 12h4m10 0h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18",
};

export function Icon({ name, className = "" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <path d={PATHS[name]} />
    </svg>
  );
}

// У каждой серьёзности своя форма — различие не держится только на цвете.
const IMPACT_SHAPES = {
  critical: <path d="M8.5 2h7L22 8.5v7L15.5 22h-7L2 15.5v-7L8.5 2Zm3.5 5v6m0 3.5v.01" />,
  serious: <path d="M12 3 2 21h20L12 3Zm0 7v5m0 3v.01" />,
  moderate: <path d="M12 2 22 12 12 22 2 12 12 2Z" />,
  minor: <path d="M5 5h14v14H5V5Z" />,
};

export function ImpactIcon({ impact }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {IMPACT_SHAPES[impact] || IMPACT_SHAPES.minor}
    </svg>
  );
}
