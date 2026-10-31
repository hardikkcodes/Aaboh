import { useState } from "react";
import { Link } from "react-router-dom";

import { useToday } from "../api/queries";
import type { SignalLevel, TodayResponse, TodayTip } from "../api/types";
import { useTemperatureUnit } from "../auth/context";
import { LiveCityMap } from "../components/live/LiveCityMap";
import { NearMeButton } from "../components/place/NearMeButton";
import { PlaceSearch } from "../components/place/PlaceSearch";
import { SavedPlaces } from "../components/place/SavedPlaces";
import { StateBadge } from "../components/ui/DataState";
import { ErrorState, LoadingPanel } from "../components/ui/Feedback";
import { ShareButton } from "../components/ui/ShareButton";
import { cn, formatHour, formatTemperature, formatTime, formatWithUnit } from "../lib/format";
import { useT } from "../lib/i18n";

const PLACE_KEY = "climatesense.place";

interface HomePlace {
  area: string;
  neighbourhood: string | null;
  label: string;
}

const DEFAULT_PLACE: HomePlace = { area: "kolkata", neighbourhood: null, label: "Kolkata" };

function storedPlace(): HomePlace {
  try {
    const raw = localStorage.getItem(PLACE_KEY);
    return raw ? (JSON.parse(raw) as HomePlace) : DEFAULT_PLACE;
  } catch {
    return DEFAULT_PLACE;
  }
}

const LEVEL_TONE: Record<SignalLevel, string> = {
  warning: "border-red-200 bg-red-50 text-red-950",
  caution: "border-amber-200 bg-amber-50 text-amber-950",
  info: "border-sky-200 bg-sky-50 text-sky-950",
  typical: "border-ink-100 bg-white text-ink-900",
  unknown: "border-ink-100 bg-ink-50 text-ink-700",
};

const SEASON_SPOTLIGHT = {
  air: { title: "Winter air watch", body: "Check the nearest station before a morning walk or run.", to: "/air-quality" },
  heat: { title: "Heat and storm season", body: "Plan around midday heat and prepare for sudden nor'westers.", to: "/safety" },
  monsoon: { title: "Monsoon mode", body: "Check your route before you leave, and report waterlogging you can see.", to: "/routes" },
  festive: { title: "Festival days", body: "Find the driest, most comfortable hours this week.", to: "/plan" },
} as const;

const QUICK_ACTIONS = [
  { to: "/report", label: "Report now", detail: "Takes seconds" },
  { to: "/routes", label: "My routes", detail: "Check your commute" },
  { to: "/plan", label: "Week planner", detail: "Best days and hours" },
  { to: "/safety", label: "Safety", detail: "Numbers and checklists" },
];

function Tile({
  label,
  value,
  detail,
  to,
  level = "typical",
}: {
  label: string;
  value: string;
  detail?: string;
  to: string;
  level?: SignalLevel;
}) {
  return (
    <Link to={to} className={cn("block rounded-xl border p-4 transition hover:border-ink-300", LEVEL_TONE[level])}>
      <p className="text-xs font-medium opacity-80">{label}</p>
      <p className="mt-1 text-2xl font-semibold leading-tight">{value}</p>
      {detail ? <p className="mt-1 text-xs leading-4 opacity-80">{detail}</p> : null}
    </Link>
  );
}

function TipRow({ tip }: { tip: TodayTip }) {
  const { t } = useT();
  return (
    <li className={cn("rounded-xl border px-3 py-2.5 text-sm leading-5", LEVEL_TONE[tip.level])}>
      {t(`tip.${tip.key}`, tip.params, tip.text)}
    </li>
  );
}

function shareText(today: TodayResponse, line: string): string {
  const tips = today.tips.slice(0, 3).map((tip) => `• ${tip.text}`);
  return [`Today in ${today.place.label}`, line, ...tips, "ClimateSense Kolkata"].join("\n");
}

function TodayBrief({ today }: { today: TodayResponse }) {
  const { t } = useT();
  const unit = useTemperatureUnit();
  const { rain, heat, air, alerts, reports } = today;
  const hasForecast = today.state !== "UNAVAILABLE";
  const rainLine = !hasForecast
    ? t("No forecast is available right now.")
    : rain.next_rain_at
      ? t("Rain likely around {time}", { time: formatTime(rain.next_rain_at) })
      : t("No rain signal in the next 24 hours");
  const windowLine = !hasForecast
    ? null
    : today.best_outdoor_window
      ? t("Best time outdoors: {start} to {end}", {
          start: formatTime(today.best_outdoor_window.start),
          end: formatTime(today.best_outdoor_window.end),
        })
      : t("No clear dry, cooler window today");

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Tile
          label={t("Rain, next 2 hours")}
          value={rain.total_mm === null ? t("Not available") : formatWithUnit(rain.total_mm, "mm")}
          detail={rainLine}
          to="/rainfall"
        />
        <Tile
          label={t("Feels like, today's peak")}
          value={heat.peak_heat_index_c === null ? t("Not available") : formatTemperature(heat.peak_heat_index_c, unit)}
          to="/weather"
          level={heat.level === "unknown" ? "typical" : heat.level}
        />
        <Tile
          label={t("Nearest station AQI")}
          value={air.aqi === null ? t("Not available") : String(air.aqi)}
          to="/air-quality"
          level={air.level === "unknown" ? "typical" : air.level}
        />
        <Tile
          label={t("Official warnings")}
          value={String(alerts.count)}
          detail={`${t("Reports nearby")}: ${reports.nearby}`}
          to="/alerts"
          level={alerts.count ? "warning" : "typical"}
        />
      </div>

      {today.timeline.length ? (
        <section aria-label={t("Next 12 hours")}>
          <h2 className="mb-2 text-sm font-semibold text-ink-800">{t("Next 12 hours")}</h2>
          <ol className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:px-0">
            {today.timeline.map((hour) => (
              <li key={hour.time} className="w-[4.6rem] shrink-0 rounded-xl border border-ink-100 bg-white p-2 text-center">
                <p className="text-[0.68rem] text-ink-500">{formatHour(hour.time)}</p>
                <p className="mt-1 text-sm font-semibold text-ink-950">{formatTemperature(hour.heat_index_c, unit, 0)}</p>
                <p className={cn("mt-0.5 text-[0.68rem]", (hour.rain_probability_pct ?? 0) >= 50 ? "font-semibold text-sky-800" : "text-ink-500")}>
                  {hour.rain_probability_pct === null ? "—" : `${hour.rain_probability_pct}%`}
                </p>
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      <div className="space-y-1 text-sm font-medium text-ink-800">
        {windowLine ? <p>{windowLine}</p> : null}
        {today.cleanest_air_window ? (
          <p>
            {t("Cleanest air: {start} to {end}", {
              start: formatTime(today.cleanest_air_window.start),
              end: formatTime(today.cleanest_air_window.end),
            })}
          </p>
        ) : null}
      </div>

      <section aria-label={t("What to do today")}>
        {today.tips.length ? (
          <ul className="space-y-2">
            {today.tips.map((tip) => <TipRow key={tip.key} tip={tip} />)}
          </ul>
        ) : (
          <p className="rounded-xl border border-ink-100 bg-white px-3 py-2.5 text-sm text-ink-700">
            {t("No strong signal right now. This is not a guarantee of safety.")}
          </p>
        )}
      </section>

      <div className="flex flex-wrap items-center gap-3">
        <StateBadge state={today.state} />
        {today.state === "STALE" ? <p className="text-xs text-amber-900">{t("The forecast may be out of date.")}</p> : null}
        <ShareButton title={`Today in ${today.place.label}`} text={shareText(today, rainLine)} />
      </div>
    </div>
  );
}

export function HomePage() {
  const { t } = useT();
  const [place, setPlace] = useState<HomePlace>(storedPlace);
  const today = useToday(place.area, place.neighbourhood);
  const season = today.data?.season ?? "air";
  const spotlight = SEASON_SPOTLIGHT[season];

  function choosePlace(next: HomePlace) {
    setPlace(next);
    try {
      localStorage.setItem(PLACE_KEY, JSON.stringify(next));
    } catch {
      // The place simply lasts for this visit.
    }
  }

  return (
    <div className="shell space-y-6 py-5 sm:py-8">
      <section>
        <h1 className="display-title">{t("Today in {place}", { place: place.label })}</h1>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <NearMeButton
            onPlace={(nearest) =>
              choosePlace({
                area: nearest.area_slug,
                neighbourhood: nearest.type === "neighbourhood" ? nearest.slug : null,
                label: nearest.name,
              })
            }
          />
          <div className="min-w-56 flex-1 sm:max-w-sm lg:hidden">
            <PlaceSearch />
          </div>
        </div>
        <SavedPlaces className="mt-3" />
      </section>

      {today.isError ? (
        <ErrorState error={today.error} onRetry={() => void today.refetch()} />
      ) : today.data ? (
        <TodayBrief today={today.data} />
      ) : (
        <LoadingPanel label="Loading today's brief" rows={3} />
      )}

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {QUICK_ACTIONS.map((action) => (
          <Link key={action.to} to={action.to} className="panel p-4 transition hover:border-ink-300">
            <p className="text-sm font-semibold text-ink-900">{t(action.label)}</p>
            <p className="mt-0.5 text-xs text-ink-500">{action.detail}</p>
          </Link>
        ))}
      </section>

      <Link to={spotlight.to} className="panel-muted block p-4 transition hover:border-ink-300">
        <p className="text-sm font-semibold text-ink-950">{spotlight.title}</p>
        <p className="mt-0.5 text-sm text-ink-600">{spotlight.body}</p>
      </Link>

      <section>
        <h2 className="section-title mb-3">{t("What residents are reporting now")}</h2>
        <LiveCityMap height="360px" />
      </section>

      <p className="text-xs leading-5 text-ink-500">
        {today.data?.note} {t("For immediate danger, call 112.")}{" "}
        <Link to="/methodology" className="underline">How this works</Link>
      </p>
    </div>
  );
}
