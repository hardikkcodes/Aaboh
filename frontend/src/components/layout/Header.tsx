import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";

import { useDataStatus } from "../../api/queries";
import { useAuth } from "../../auth/context";
import { PlaceSearch } from "../place/PlaceSearch";
import { cn } from "../../lib/format";
import { NAV_ITEMS, PRIMARY_NAV_ITEMS, SECONDARY_NAV_ITEMS } from "../../lib/constants";

function BrandMark() {
  return (
    <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-ink-900 text-white shadow-sm" aria-hidden="true">
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M12 3c3.2 3.4 5.5 6.2 5.5 9.2A5.5 5.5 0 0 1 12 17.7a5.5 5.5 0 0 1-5.5-5.5C6.5 9.2 8.8 6.4 12 3Z" />
        <path d="M9.2 12.6c.5 1.4 1.5 2.2 2.8 2.4" />
      </svg>
    </span>
  );
}

export function Header() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);
  const { user, isAuthenticated, logout } = useAuth();
  const { data: status } = useDataStatus();
  const location = useLocation();

  useEffect(() => {
    setMobileOpen(false);
    setMoreOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    function handleClick(event: MouseEvent) {
      if (!moreRef.current?.contains(event.target as Node)) setMoreOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const unavailable = status
    ? Object.values(status.modules).filter((module) => module.state !== "AVAILABLE").length
    : 0;

  return (
    <header className="sticky top-0 z-40 border-b border-ink-100 bg-mist/90 backdrop-blur">
      <div className="shell flex h-16 items-center justify-between gap-4">
        <Link to="/" className="flex shrink-0 items-center gap-2.5" aria-label="ClimateSense Kolkata home">
          <BrandMark />
          <span className="leading-none">
            <span className="block font-display text-lg text-ink-950">ClimateSense</span>
            <span className="mt-0.5 block text-[0.62rem] font-semibold uppercase tracking-[0.18em] text-ink-500">
              Kolkata
            </span>
          </span>
        </Link>

        <nav className="hidden items-center gap-0.5 xl:flex" aria-label="Main navigation">
          {PRIMARY_NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={"end" in item ? item.end : false}
              className={({ isActive }) =>
                cn(
                  "rounded-full px-2.5 py-2 text-[0.78rem] font-medium transition",
                  isActive ? "bg-ink-900 text-white" : "text-ink-600 hover:bg-ink-100 hover:text-ink-900",
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
          <div className="relative" ref={moreRef}>
            <button
              type="button"
              onClick={() => setMoreOpen((open) => !open)}
              aria-expanded={moreOpen}
              className={cn(
                "rounded-full px-2.5 py-2 text-[0.78rem] font-medium transition",
                moreOpen ? "bg-ink-100 text-ink-900" : "text-ink-600 hover:bg-ink-100 hover:text-ink-900",
              )}
            >
              More
            </button>
            {moreOpen ? (
              <div className="absolute right-0 mt-2 w-52 overflow-hidden rounded-xl border border-ink-100 bg-white py-1 shadow-panel">
                {SECONDARY_NAV_ITEMS.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      cn(
                        "block px-3 py-2 text-sm",
                        isActive ? "bg-ink-900 text-white" : "text-ink-700 hover:bg-ink-50",
                      )
                    }
                  >
                    {item.label}
                  </NavLink>
                ))}
              </div>
            ) : null}
          </div>
        </nav>

        <div className="flex items-center gap-2">
          <div className="hidden lg:block">
            <PlaceSearch />
          </div>
          <Link
            to="/methodology"
            className="hidden items-center gap-1.5 rounded-full border border-ink-200 bg-white px-2.5 py-1.5 text-[0.7rem] font-medium text-ink-600 hover:border-ink-300 md:flex"
            title="Data availability and methodology"
          >
            <span
              className={cn("h-1.5 w-1.5 rounded-full", unavailable ? "bg-amber-500" : "bg-emerald-500")}
              aria-hidden="true"
            />
            {status ? `${6 - unavailable}/6 layers` : "Data status"}
          </Link>

          {isAuthenticated ? (
            <Link to="/account" className="btn-secondary hidden !px-3 !py-1.5 text-xs sm:inline-flex">
              {user?.display_name || "Account"}
            </Link>
          ) : (
            <Link to="/login" className="btn-secondary hidden !px-3 !py-1.5 text-xs sm:inline-flex">
              Log in
            </Link>
          )}
          <Link to="/reports/new" className="btn-primary hidden !px-3 !py-1.5 text-xs sm:inline-flex">
            Report an issue
          </Link>

          <button
            type="button"
            className="rounded-full border border-ink-200 bg-white p-2 text-ink-700 xl:hidden"
            onClick={() => setMobileOpen((open) => !open)}
            aria-expanded={mobileOpen}
            aria-label="Toggle navigation menu"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
              {mobileOpen ? <path d="M6 6l12 12M18 6 6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
            </svg>
          </button>
        </div>
      </div>

      {mobileOpen ? (
        <div className="border-t border-ink-100 bg-white xl:hidden">
          <div className="shell space-y-3 py-4">
            <PlaceSearch size="lg" />
            <div className="grid gap-1 sm:grid-cols-2">
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={"end" in item ? item.end : false}
                  className={({ isActive }) =>
                    cn(
                      "rounded-lg px-3 py-2.5 text-sm font-medium",
                      isActive ? "bg-ink-900 text-white" : "text-ink-700 hover:bg-ink-50",
                    )
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
            <div className="flex flex-wrap gap-2 border-t border-ink-100 pt-3">
              {isAuthenticated ? (
                <>
                  <Link to="/account" className="btn-secondary text-xs">
                    {user?.display_name || "Account"}
                  </Link>
                  <button type="button" className="btn-ghost text-xs" onClick={() => void logout()}>
                    Log out
                  </button>
                </>
              ) : (
                <>
                  <Link to="/login" className="btn-secondary text-xs">
                    Log in
                  </Link>
                  <Link to="/register" className="btn-ghost text-xs">
                    Create account
                  </Link>
                </>
              )}
              <Link to="/reports/new" className="btn-primary text-xs">
                Report an issue
              </Link>
            </div>
          </div>
        </div>
      ) : null}
    </header>
  );
}
