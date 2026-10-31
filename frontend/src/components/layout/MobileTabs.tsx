import { Menu, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";

import { useAuth } from "../../auth/context";
import { cn } from "../../lib/format";
import { useT } from "../../lib/i18n";
import { NAV_GROUPS, NavIcon, NavList } from "./Navigation";

const [NOW, PLAN] = NAV_GROUPS;
const TABS = [NOW.items[0], NOW.items[1], PLAN.items[0]];

/** Thumb-reach navigation: daily destinations, reporting, and everything else in a sheet. */
export function MobileTabs() {
  const { t } = useT();
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  const [open, setOpen] = useState(false);

  useEffect(() => setOpen(false), [location.pathname]);

  const tabClasses = "flex min-h-14 flex-col items-center justify-center gap-0.5 text-[0.68rem] font-semibold";

  return (
    <>
      {open ? (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label={t("More")}>
          <button type="button" className="absolute inset-0 bg-ink-950/40" aria-label="Close menu" onClick={() => setOpen(false)} />
          <div className="absolute inset-x-0 bottom-0 max-h-[80vh] overflow-y-auto rounded-t-2xl bg-white p-4 pb-20">
            <NavList onNavigate={() => setOpen(false)} />
            <Link to={isAuthenticated ? "/account" : "/login"} className="btn-secondary mt-4 w-full">
              {isAuthenticated ? "Account" : t("Log in")}
            </Link>
            {isAuthenticated ? null : (
              <Link to="/register" className="btn-primary mt-2 w-full">{t("Sign up")}</Link>
            )}
          </div>
        </div>
      ) : null}
      <nav
        className="fixed inset-x-0 bottom-0 z-50 grid grid-cols-5 border-t border-ink-100 bg-white pb-[env(safe-area-inset-bottom)] lg:hidden"
        aria-label="Quick navigation"
      >
        {TABS.slice(0, 2).map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.to === "/"}
            className={({ isActive }) => cn(tabClasses, isActive ? "text-ink-950" : "text-ink-500")}
          >
            <NavIcon icon={tab.icon} />
            {t(tab.label)}
          </NavLink>
        ))}
        <Link to="/report" className={cn(tabClasses, "text-ink-950")}>
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-ink-900 text-white">
            <NavIcon icon={Plus} />
          </span>
          {t("Report")}
        </Link>
        <NavLink to={TABS[2].to} className={({ isActive }) => cn(tabClasses, isActive ? "text-ink-950" : "text-ink-500")}>
          <NavIcon icon={TABS[2].icon} />
          {t("Routes")}
        </NavLink>
        <button type="button" className={cn(tabClasses, "text-ink-500")} aria-expanded={open} onClick={() => setOpen(!open)}>
          <NavIcon icon={Menu} />
          {t("More")}
        </button>
      </nav>
    </>
  );
}
