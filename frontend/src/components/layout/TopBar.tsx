import { Bell, LogIn, Moon, Plus, Sun, UserPlus, UserRound } from "lucide-react";
import { Link } from "react-router-dom";

import { useNotifications } from "../../api/queries";
import { useAuth } from "../../auth/context";
import { useT } from "../../lib/i18n";
import { PlaceSearch } from "../place/PlaceSearch";
import { usePreferences } from "../../lib/preferences";
import { AreaPicker } from "./AreaPicker";
import { BrandMark, Wordmark } from "./Brand";
import { NavIcon } from "./Navigation";

export function TopBar() {
  const { user, isAuthenticated } = useAuth();
  const { t, lang, setLang } = useT();
  const notifications = useNotifications(isAuthenticated);
  const unread = notifications.data?.unread ?? 0;
  const { theme, setTheme } = usePreferences();
  const isDark = theme === "dark" || (theme === "system" && document.documentElement.classList.contains("dark"));

  return (
    <header className="sticky top-0 z-40 border-b border-ink-100 bg-white/95 backdrop-blur">
      <div className="flex h-14 items-center gap-3 px-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2 lg:hidden" aria-label="Aaboh Kolkata home">
          <BrandMark />
          <Wordmark className="hidden sm:block" />
        </Link>
        <div className="hidden flex-1 lg:block">
          <PlaceSearch />
        </div>
        <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
          <AreaPicker />
          <button
            type="button"
            className="rounded-full border border-ink-200 p-1.5 text-ink-700 hover:bg-ink-50"
            onClick={() => setTheme(isDark ? "light" : "dark")}
            aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
          >
            <NavIcon icon={isDark ? Sun : Moon} />
          </button>
          <button
            type="button"
            className="rounded-full border border-ink-200 px-2.5 py-1.5 text-xs font-semibold text-ink-700 hover:bg-ink-50"
            onClick={() => setLang(lang === "bn" ? "en" : "bn")}
            aria-label={lang === "bn" ? "Switch to English" : "বাংলায় দেখুন"}
          >
            {lang === "bn" ? "EN" : "বাং"}
          </button>
          {isAuthenticated ? (
            <Link
              to="/notifications"
              className="relative rounded-full border border-ink-200 p-1.5 text-ink-700 hover:bg-ink-50"
              aria-label={`${t("Notifications")}: ${unread}`}
            >
              <NavIcon icon={Bell} />
              {unread ? (
                <span className="absolute -right-1 -top-1 rounded-full bg-red-600 px-1 text-[0.6rem] font-bold text-white">
                  {unread}
                </span>
              ) : null}
            </Link>
          ) : null}
          <Link to={isAuthenticated ? "/account" : "/login"} className="btn-secondary hidden !px-3 !py-1.5 text-xs sm:inline-flex">
            {isAuthenticated ? <UserRound className="mr-1 h-3.5 w-3.5" aria-hidden="true" /> : <LogIn className="mr-1 h-3.5 w-3.5" aria-hidden="true" />}
            {isAuthenticated ? user?.display_name || "Account" : t("Log in")}
          </Link>
          {isAuthenticated ? null : (
            <Link to="/register" className="btn-secondary hidden !px-3 !py-1.5 text-xs sm:inline-flex">
              <UserPlus className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
              {t("Sign up")}
            </Link>
          )}
          <Link to="/report" className="btn-primary hidden !px-3 !py-1.5 text-xs sm:inline-flex">
            <Plus className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
            {t("Report")}
          </Link>
        </div>
      </div>
    </header>
  );
}
