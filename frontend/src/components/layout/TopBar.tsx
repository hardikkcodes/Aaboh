import { Link } from "react-router-dom";

import { useNotifications } from "../../api/queries";
import { useAuth } from "../../auth/context";
import { useT } from "../../lib/i18n";
import { PlaceSearch } from "../place/PlaceSearch";
import { BrandMark, NavIcon } from "./Navigation";

export function TopBar() {
  const { user, isAuthenticated } = useAuth();
  const { t, lang, setLang } = useT();
  const notifications = useNotifications(isAuthenticated);
  const unread = notifications.data?.unread ?? 0;

  return (
    <header className="sticky top-0 z-40 border-b border-ink-100 bg-white/95 backdrop-blur">
      <div className="flex h-14 items-center gap-3 px-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2 lg:hidden" aria-label="ClimateSense Kolkata home">
          <BrandMark />
          <span className="text-[0.95rem] font-semibold text-ink-950">ClimateSense</span>
        </Link>
        <div className="hidden flex-1 lg:block">
          <PlaceSearch />
        </div>
        <div className="ml-auto flex items-center gap-2">
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
              <NavIcon path="M6 9a6 6 0 1 1 12 0c0 6 2.5 7 2.5 7h-17S6 15 6 9ZM10 20a2 2 0 0 0 4 0" />
              {unread ? (
                <span className="absolute -right-1 -top-1 rounded-full bg-red-600 px-1 text-[0.6rem] font-bold text-white">
                  {unread}
                </span>
              ) : null}
            </Link>
          ) : null}
          <Link to={isAuthenticated ? "/account" : "/login"} className="btn-secondary hidden !px-3 !py-1.5 text-xs sm:inline-flex">
            {isAuthenticated ? user?.display_name || "Account" : t("Log in")}
          </Link>
          <Link to="/report" className="btn-primary hidden !px-3 !py-1.5 text-xs sm:inline-flex">
            {t("Report")}
          </Link>
        </div>
      </div>
    </header>
  );
}
