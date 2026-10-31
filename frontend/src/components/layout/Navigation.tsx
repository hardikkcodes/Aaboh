import {
  BookOpen,
  CalendarDays,
  CloudRain,
  CloudSun,
  FileText,
  Lightbulb,
  MapPin,
  Route,
  ShieldCheck,
  Sun,
  Thermometer,
  Trees,
  TrendingUp,
  TriangleAlert,
  Users,
  Wind,
  type LucideIcon,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { cn } from "../../lib/format";
import { useT } from "../../lib/i18n";

export const NAV_GROUPS = [
  {
    title: "Now",
    items: [
      { to: "/", label: "Today", icon: Sun },
      { to: "/live", label: "Live map", icon: MapPin },
      { to: "/alerts", label: "Official alerts", icon: TriangleAlert },
    ],
  },
  {
    title: "Plan",
    items: [
      { to: "/routes", label: "My routes", icon: Route },
      { to: "/plan", label: "Week planner", icon: CalendarDays },
      { to: "/spots", label: "Cool spots", icon: Trees },
      { to: "/safety", label: "Safety", icon: ShieldCheck },
    ],
  },
  {
    title: "Explore",
    items: [
      { to: "/weather", label: "Weather", icon: CloudSun },
      { to: "/rainfall", label: "Rainfall", icon: CloudRain },
      { to: "/air-quality", label: "Air quality", icon: Wind },
      { to: "/heat", label: "Heat & environment", icon: Thermometer },
      { to: "/climate", label: "Climate", icon: TrendingUp },
      { to: "/reports", label: "Community", icon: Users },
      { to: "/insights", label: "Insights", icon: Lightbulb },
      { to: "/learn", label: "Learn", icon: BookOpen },
      { to: "/methodology", label: "Methodology", icon: FileText },
    ],
  },
] as const;

export function NavIcon({ icon: Icon }: { icon: LucideIcon }) {
  return <Icon className="h-[1.1rem] w-[1.1rem] shrink-0" strokeWidth={1.9} aria-hidden="true" />;
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
                  <NavIcon icon={item.icon} />
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
