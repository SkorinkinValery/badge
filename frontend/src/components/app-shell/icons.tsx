"use client";

export type NavIconType =
  | "grid"
  | "list"
  | "mic"
  | "up"
  | "user"
  | "team"
  | "doc"
  | "chart"
  | "gear";

export function NavIcon({ type, color }: { type: NavIconType; color?: string }) {
  const c = color || "currentColor";
  const p = { fill: "none", stroke: c, strokeWidth: 1.6 };
  const m = { shapeRendering: "crispEdges" as const };
  switch (type) {
    case "grid":
      return (
        <svg width="15" height="15" viewBox="0 0 15 15" style={m}>
          <rect x="1" y="1" width="5" height="5" {...p} />
          <rect x="9" y="1" width="5" height="5" {...p} />
          <rect x="1" y="9" width="5" height="5" {...p} />
          <rect x="9" y="9" width="5" height="5" {...p} />
        </svg>
      );
    case "list":
      return (
        <svg width="15" height="15" viewBox="0 0 15 15" style={m}>
          <rect x="1" y="2" width="3" height="3" fill={c} />
          <line x1="6" y1="3.5" x2="14" y2="3.5" stroke={c} strokeWidth="1.4" />
          <rect x="1" y="10" width="3" height="3" fill={c} />
          <line x1="6" y1="11.5" x2="14" y2="11.5" stroke={c} strokeWidth="1.4" />
        </svg>
      );
    case "mic":
      return (
        <svg width="15" height="15" viewBox="0 0 15 15" style={m}>
          <rect x="5.5" y="1.5" width="4" height="7" {...p} />
          <path d="M3 7.5a4.5 4.5 0 0 0 9 0" {...p} />
          <line x1="7.5" y1="12" x2="7.5" y2="14" stroke={c} strokeWidth="1.4" />
        </svg>
      );
    case "up":
      return (
        <svg width="15" height="15" viewBox="0 0 15 15" style={m}>
          <line x1="7.5" y1="2" x2="7.5" y2="10" stroke={c} strokeWidth="1.6" />
          <polyline points="4,5 7.5,1.5 11,5" {...p} />
          <line x1="2" y1="13" x2="13" y2="13" stroke={c} strokeWidth="1.6" />
        </svg>
      );
    case "user":
      return (
        <svg width="15" height="15" viewBox="0 0 15 15" style={m}>
          <circle cx="7.5" cy="4.5" r="2.6" {...p} />
          <path d="M2.5 13c0-2.8 2.2-4.5 5-4.5s5 1.7 5 4.5" {...p} />
        </svg>
      );
    case "team":
      return (
        <svg width="15" height="15" viewBox="0 0 15 15" style={m}>
          <circle cx="5" cy="5" r="2" {...p} />
          <circle cx="10.5" cy="5.5" r="1.7" {...p} />
          <path d="M1.5 12c0-2 1.5-3.2 3.5-3.2S8.5 10 8.5 12" {...p} />
        </svg>
      );
    case "doc":
      return (
        <svg width="15" height="15" viewBox="0 0 15 15" style={m}>
          <rect x="3" y="1.5" width="9" height="12" {...p} />
          <line x1="5" y1="5" x2="10" y2="5" stroke={c} strokeWidth="1.2" />
          <line x1="5" y1="7.5" x2="10" y2="7.5" stroke={c} strokeWidth="1.2" />
          <line x1="5" y1="10" x2="8" y2="10" stroke={c} strokeWidth="1.2" />
        </svg>
      );
    case "chart":
      return (
        <svg width="15" height="15" viewBox="0 0 15 15" style={m}>
          <rect x="2" y="8" width="3" height="5" fill={c} />
          <rect x="6" y="5" width="3" height="8" fill={c} />
          <rect x="10" y="2" width="3" height="11" fill={c} />
        </svg>
      );
    case "gear":
      return (
        <svg width="15" height="15" viewBox="0 0 15 15" style={m}>
          <circle cx="7.5" cy="7.5" r="2.4" {...p} />
          <path
            d="M7.5 1.5v2M7.5 11.5v2M1.5 7.5h2M11.5 7.5h2M3.3 3.3l1.4 1.4M10.3 10.3l1.4 1.4M11.7 3.3l-1.4 1.4M4.7 10.3l-1.4 1.4"
            stroke={c}
            strokeWidth="1.2"
          />
        </svg>
      );
    default:
      return null;
  }
}

export interface NavItem {
  r: string;
  label: string;
  icon: NavIconType;
  admin?: boolean;
}
export interface NavSection {
  sec: string;
  admin?: boolean;
  items: NavItem[];
}

export const NAV: NavSection[] = [
  {
    sec: "Звонки",
    items: [
      { r: "/dashboard", label: "Дашборд", icon: "grid" },
      { r: "/recordings", label: "Записи", icon: "list" },
      { r: "/recordings/record", label: "Запись с микрофона", icon: "mic" },
      { r: "/recordings/upload", label: "Загрузить запись", icon: "up", admin: true },
    ],
  },
  {
    sec: "Администрирование",
    admin: true,
    items: [
      { r: "/admin/users", label: "Пользователи", icon: "user" },
      { r: "/admin/managers", label: "Менеджеры", icon: "team" },
      { r: "/admin/scripts", label: "Скрипты", icon: "doc" },
      { r: "/admin/summary", label: "Дневная сводка", icon: "chart" },
      { r: "/admin/settings", label: "Настройки", icon: "gear" },
    ],
  },
];
