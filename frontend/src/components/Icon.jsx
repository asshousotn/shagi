const paths = {
  home: <path d="M3 10.5 12 3l9 7.5M5 9v12h14V9" />,
  list: <><rect x="4" y="4" width="16" height="16" rx="2" /><path d="M8 9h8M8 13h8" /></>,
  plus: <path d="M12 5v14M5 12h14" />,
  user: <><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 4-6 8-6s8 2 8 6" /></>,
  trophy: <><path d="M8 4h8v4a4 4 0 0 1-8 0V4zM6 4h2v2H6zM18 4h-2v2h2zM12 12v4M8 20h8" /></>,
  download: <path d="M12 3v12m0 0 4-4m-4 4-4-4M4 19h16" />,
  up: <><path d="M7 10v10H4V10h3zM7 10l4-7 2 1-1 6h5a2 2 0 0 1 2 2l-1 7H7" /></>,
  down: <><path d="M7 14V4H4v10h3zM7 14l4 7 2-1-1-6h5a2 2 0 0 0 2-2l-1-7H7" /></>,
  chat: <path d="M21 12a8 8 0 0 1-8 8H7l-4 3 1-5a8 8 0 1 1 17-6z" />,
  spark: <path d="M12 3v6M12 15v6M3 12h6M15 12h6M6 6l3 3M15 15l3 3M18 6l-3 3M9 15l-3 3" />,
  branch: <><circle cx="6" cy="5" r="2" /><circle cx="18" cy="19" r="2" /><path d="M6 7v8a4 4 0 0 0 4 4h6" /></>,
  star: <path d="m12 2 3 7 7 .6-5.3 4.6 1.6 7-6.3-3.8L5.7 21l1.6-7L2 9.6 9 9l3-7z" />,
  left: <path d="M15 18l-6-6 6-6" />,
  check: <path d="M20 6L9 17l-5-5" />,
  warning: <><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><path d="M12 9v4M12 17h.01" /></>,
  search: <><circle cx="11" cy="11" r="8" /><path d="m21 21-4-4" /></>,
  close: <path d="M18 6 6 18M6 6l12 12" />,
  bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><path d="M10 21h4" /></>,
  history: <><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 3v5h5M12 7v5l4 2" /></>,
  menu: <path d="M4 7h16M4 12h16M4 17h16" />
};

export default function Icon({ name, size = 18, className = "" }) {
  const filled = name === "star";
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={filled ? "currentColor" : "none"}
      stroke={filled ? "none" : "currentColor"}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {paths[name] || null}
    </svg>
  );
}
