import type { ClimatePoint, ClimateTrendsResponse } from "../../api/types";
import { LONG_TERM_ACTIONS } from "../../lib/explainers";
import { formatNumber } from "../../lib/format";

const SEASON_NAMES: Record<string, string> = {
  DJF: "winter (Dec to Feb)",
  MAM: "summer (Mar to May)",
  JJA: "monsoon (Jun to Aug)",
  SON: "autumn (Sep to Nov)",
};
const COMPARE_YEARS = 10;

function average(points: ClimatePoint[]): number | null {
  const values = points.flatMap((point) => (point.value === null ? [] : [point.value]));
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}

function peak(points: ClimatePoint[]): ClimatePoint | null {
  return points.reduce<ClimatePoint | null>(
    (best, point) => (point.value !== null && (best?.value ?? -Infinity) < point.value ? point : best),
    null,
  );
}

function change(points: ClimatePoint[]) {
  if (points.length < COMPARE_YEARS * 2) return null;
  const before = average(points.slice(0, COMPARE_YEARS));
  const after = average(points.slice(-COMPARE_YEARS));
  if (before === null || after === null) return null;
  return {
    before,
    after,
    firstYears: `${points[0].year}–${points[COMPARE_YEARS - 1].year}`,
    lastYears: `${points[points.length - COMPARE_YEARS].year}–${points[points.length - 1].year}`,
  };
}

function Fact({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-xl border border-ink-100 bg-white p-3">
      <p className="text-lg font-semibold text-ink-950">{value}</p>
      <p className="mt-0.5 text-xs leading-5 text-ink-600">{label}</p>
    </div>
  );
}

/** A plain-language reading of the long-term record, using only stored values. */
export function ClimateStory({ climate }: { climate: ClimateTrendsResponse }) {
  const temperature = climate.series.annual_temperature ?? [];
  const hotDays = climate.series.hot_days_ge_35c ?? [];
  const rain = climate.series.annual_precipitation ?? [];
  const heavy = climate.series.heavy_rain_days_ge_50mm ?? [];
  const warming = climate.trends.annual_temperature;
  const warmth = change(temperature);
  const hot = change(hotDays);
  const hottest = peak(temperature);
  const wettest = peak(rain);
  const heavyChange = change(heavy);
  if (!warming || !warmth) return null;

  const seasons = Object.entries(climate.trends.seasonal_temperature ?? {}).flatMap(([season, trend]) =>
    trend ? [{ season, slope: trend.slope_per_decade }] : [],
  );
  const fastest = seasons.reduce<(typeof seasons)[number] | null>(
    (best, item) => (!best || item.slope > best.slope ? item : best),
    null,
  );

  return (
    <section className="panel-muted space-y-3 p-4">
      <div>
        <h2 className="section-title">What has changed here</h2>
        <p className="mt-1 text-sm leading-6 text-ink-700">
          The last {COMPARE_YEARS} years averaged {formatNumber(warmth.after, 1)}°C, compared with{" "}
          {formatNumber(warmth.before, 1)}°C in {warmth.firstYears}. That's a change of{" "}
          {warmth.after >= warmth.before ? "+" : ""}
          {formatNumber(warmth.after - warmth.before, 1)}°C.
          {fastest ? ` ${SEASON_NAMES[fastest.season] ?? fastest.season} has changed the most.` : ""}
        </p>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {hot ? (
          <Fact
            value={`${formatNumber(hot.before, 0)} → ${formatNumber(hot.after, 0)}`}
            label={`Days a year reaching 35°C, ${hot.firstYears} to ${hot.lastYears}`}
          />
        ) : null}
        {heavyChange ? (
          <Fact
            value={`${formatNumber(heavyChange.before, 1)} → ${formatNumber(heavyChange.after, 1)}`}
            label="Days a year with 50 mm or more of rain"
          />
        ) : null}
        {hottest ? <Fact value={String(hottest.year)} label={`Hottest year on this record, ${formatNumber(hottest.value, 1)}°C`} /> : null}
        {wettest ? <Fact value={String(wettest.year)} label={`Wettest year on this record, ${formatNumber(wettest.value, 0)} mm`} /> : null}
      </div>
      <div>
        <h3 className="text-sm font-semibold text-ink-900">What you can do</h3>
        <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm leading-6 text-ink-700">
          {LONG_TERM_ACTIONS.map((action) => <li key={action}>{action}</li>)}
        </ul>
      </div>
      <p className="text-xs leading-5 text-ink-500">
        Modelled area-wide history, not neighbourhood measurements. Single years vary, and this does not explain the cause.
      </p>
    </section>
  );
}
