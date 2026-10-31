import { NavLink } from "react-router-dom";

import { cn } from "../../lib/format";
import { useT } from "../../lib/i18n";

export const NAV_GROUPS = [
  {
    title: "Now",
    items: [
      { to: "/", label: "Today", icon: "M12 3v2M12 19v2M3 12h2M19 12h2M6 6l1.5 1.5M16.5 16.5 18 18M6 18l1.5-1.5M16.5 7.5 18 6M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z" },
      { to: "/live", label: "Live map", icon: "M12 21s7-6.1 7-11a7 7 0 1 0-14 0c0 4.9 7 11 7 11ZM12 12a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z" },
      { to: "/alerts", label: "Official alerts", icon: "M12 4 3 20h18L12 4ZM12 10v4M12 17h.01" },
    ],
  },
  {
    title: "Plan",
    items: [
      { to: "/routes", label: "My routes", icon: "M6 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM18 9a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM6 15V9a2 2 0 0 1 2-2h8M18 9v6a2 2 0 0 1-2 2H8" },
      { to: "/plan", label: "Week planner", icon: "M5 6h14v14H5zM5 10h14M9 3v4M15 3v4" },
      { to: "/spots", label: "Cool spots", icon: "M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11Z" },
      { to: "/safety", label: "Safety", icon: "M12 3 5 6v5c0 4.5 3 8 7 10 4-2 7-5.5 7-10V6l-7-3Z" },
    ],
  },
  {
    title: "Explore",
    items: [
      { to: "/weather", label: "Weather", icon: "M7 18a4 4 0 0 1 0-8 5 5 0 0 1 9.6-1.3A4.5 4.5 0 0 1 17 18H7Z" },
      { to: "/rainfall", label: "Rainfall", icon: "M7 14a4 4 0 0 1 0-8 5 5 0 0 1 9.6-1.3A4.5 4.5 0 0 1 17 14H7ZM9 17l-1 3M13 17l-1 3M17 17l-1 3" },
      { to: "/air-quality", label: "Air quality", icon: "M3 9h11a3 3 0 1 0-3-3M3 14h15a3 3 0 1 1-3 3M3 19h6" },
      { to: "/heat", label: "Heat & environment", icon: "M12 14V5a2 2 0 1 0-4 0v9a4 4 0 1 0 4 0Z" },
      { to: "/climate", label: "Climate", icon: "M4 19V5M4 19h16M8 15l3-4 3 2 5-7" },
      { to: "/reports", label: "Community", icon: "M9 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM3 20a6 6 0 0 1 12 0M16 5a3 3 0 0 1 0 6M18 14a6 6 0 0 1 3 6" },
      { to: "/insights", label: "Insights", icon: "M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3Z" },
      { to: "/models", label: "Model status", icon: "M5 5h14v14H5zM9 9h6v6H9zM9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" },
      { to: "/methodology", label: "Methodology", icon: "M5 4h11l3 3v13H5zM9 9h6M9 13h6M9 17h4" },
    ],
  },
] as const;

export function NavIcon({ path }: { path: string }) {
  return (
    <svg viewBox="0 0 24 24" className="h-[1.1rem] w-[1.1rem] shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={path} />
    </svg>
  );
}

export function BrandMark() {
  return (
    <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-ink-900 text-white" aria-hidden="true">
      <NavIcon path="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11Z" />
    </span>
  );
}

export function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const { t } = useT();
  return (
    <div className="space-y-5">
      {NAV_GROUPS.map((group) => (
        <div key={group.title}>
          <p className="mb-1 px-3 text-[0.7rem] font-semibold text-ink-400">{group.title}</p>
          <ul className="space-y-0.5">
            {group.items.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === "/"}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition",
                      isActive ? "bg-ink-900 text-white" : "text-ink-700 hover:bg-ink-100",
                    )
                  }
                >
                  <NavIcon path={item.icon} />
                  {t(item.label)}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
