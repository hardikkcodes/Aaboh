import { useEffect } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";

import { Footer } from "./Footer";
import { MobileTabs } from "./MobileTabs";
import { BrandMark, NavList } from "./Navigation";
import { TopBar } from "./TopBar";

export function AppLayout() {
  const location = useLocation();

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior });
  }, [location.pathname]);

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[15rem_minmax(0,1fr)]">
      <aside className="sticky top-0 hidden h-screen overflow-y-auto border-r border-ink-100 bg-white p-3 lg:block">
        <Link to="/" className="mb-5 flex items-center gap-2 px-2 pt-1" aria-label="ClimateSense Kolkata home">
          <BrandMark />
          <span className="leading-tight">
            <span className="block text-[0.95rem] font-semibold text-ink-950">ClimateSense</span>
            <span className="block text-xs text-ink-500">Kolkata</span>
          </span>
        </Link>
        <nav aria-label="Main navigation">
          <NavList />
        </nav>
      </aside>
      <div className="flex min-h-screen min-w-0 flex-col pb-16 lg:pb-0">
        <TopBar />
        <main className="flex-1">
          <Outlet />
        </main>
        <Footer />
      </div>
      <MobileTabs />
    </div>
  );
}
