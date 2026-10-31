import { Link } from "react-router-dom";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useClimateTrends } from "../api/queries";
import type { ClimatePoint } from "../api/types";
import { DataStateNotice, StateBadge } from "../components/ui/DataState";
import { ErrorState, LoadingPanel } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";
import { SectionHeading } from "../components/ui/SectionHeading";
import { SourcePanel } from "../components/ui/SourcePanel";
import { StatCard } from "../components/ui/StatCard";
import { formatNumber, titleCase } from "../lib/format";

function annualTemperatureData(points: ClimatePoint[] = []) {
  return points.map((point) => ({
    year: point.year,
    mean: point.value,
    anomaly: point.anomaly,
  }));
}

function annualRainData(points: ClimatePoint[] = []) {
  return points.map((point) => ({ year: point.year, value: point.value }));
}

function countData(points: ClimatePoint[] = []) {
  return points.map((point) => ({ year: point.year, value: point.value }));
}

function seasonalData(series: Record<string, ClimatePoint[]> | undefined) {
  if (!series) return { data: [], seasons: [] as string[] };
  const seasons = Object.keys(series).filter((season) => series[season]?.length);
  const yearMap = new Map<number, Record<string, number | null>>();
  for (const season of seasons) {
    for (const point of series[season]) {
      const row = yearMap.get(point.year) ?? { year: point.year };
      row[season] = point.value;
      yearMap.set(point.year, row);
    }
  }
  const data = Array.from(yearMap.values()).sort((a, b) => Number(a.year) - Number(b.year));
  return { data, seasons };
}

const seasonColors: Record<string, string> = {
  DJF: "#1d4ed8",
  MAM: "#d97706",
  JJA: "#0f766e",
  SON: "#9a3412",
};

export function ClimatePage() {
  const climate = useClimateTrends();
  const data = climate.data;
  const tempData = annualTemperatureData(data?.series.annual_temperature);
  const rainData = annualRainData(data?.series.annual_precipitation);
  const hotDays = countData(data?.series.hot_days_ge_35c);
  const heavyRain = countData(data?.series.heavy_rain_days_ge_50mm);
  const seasonal = seasonalData(data?.series.seasonal_temperature);

  const latestTemp = tempData.at(-1);
  const tempTrend = data?.trends.annual_temperature;
  const rainTrend = data?.trends.annual_precipitation;

  return (
    <div className="shell space-y-10 py-10 sm:py-14">
      <PageHeader
        eyebrow="Climate · ERA5-Land reanalysis"
        title="Long-term context for a hotter, wetter city"
        description="Annual and seasonal metrics from ERA5-Land reanalysis (~9 km). These are area-level values for context, not neighbourhood observations, forecasts or causal attribution."
        aside={data ? <StateBadge state={data.state} /> : null}
      />

      {climate.isError ? (
        <ErrorState error={climate.error} onRetry={() => void climate.refetch()} />
      ) : climate.isLoading ? (
        <LoadingPanel label="Loading climate series" />
      ) : !data || data.state === "UNAVAILABLE" ? (
        <>
          <DataStateNotice
            state="UNAVAILABLE"
            title="No climate metrics are available"
            reason={data?.reason}
          >
            <p>
              The platform has not synthesised a climate trend. The ERA5-Land ingestion command can
              populate this page when archive access succeeds; until then, every chart would be empty
              and no slope is reported.
            </p>
          </DataStateNotice>
          <SourcePanel source={data?.source} note={data?.methodology} />
        </>
      ) : (
        <>
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Latest annual mean"
              value={latestTemp?.mean !== null && latestTemp?.mean !== undefined ? `${formatNumber(latestTemp.mean, 1)}°C` : "—"}
              detail={latestTemp ? `${latestTemp.year} complete calendar year` : "No complete year"}
              tone="warm"
            />
            <StatCard
              label="Temperature anomaly"
              value={latestTemp?.anomaly !== null && latestTemp?.anomaly !== undefined ? `${latestTemp.anomaly >= 0 ? "+" : ""}${formatNumber(latestTemp.anomaly, 2)}°C` : "—"}
              detail="Versus the 1991–2020 annual mean baseline"
              tone="warm"
            />
            <StatCard
              label="Decadal slope"
              value={tempTrend ? `${tempTrend.slope_per_decade >= 0 ? "+" : ""}${formatNumber(tempTrend.slope_per_decade, 2)}°C` : "—"}
              detail={tempTrend ? `OLS over ${tempTrend.n_years} years (${tempTrend.start_year}–${tempTrend.end_year}); descriptive only` : "At least 5 annual points are required"}
            />
            <StatCard
              label="Hot days (≥ 35°C)"
              value={hotDays.at(-1)?.value !== null && hotDays.at(-1)?.value !== undefined ? formatNumber(hotDays.at(-1)?.value, 0) : "—"}
              detail={hotDays.at(-1) ? `Latest complete year (${hotDays.at(-1)?.year})` : "No annual count"}
              tone="alert"
            />
          </section>

          <section>
            <SectionHeading
              eyebrow="Annual temperature"
              title="Mean temperature and anomaly"
              description="Bars show the anomaly against the documented baseline; the line shows the annual mean."
              action={data ? <StateBadge state={data.state} /> : null}
            />
            {tempData.length ? (
              <div className="panel mt-5 p-4 sm:p-6">
                <div className="h-80 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={tempData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                      <CartesianGrid stroke="#e3ebe8" strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="year" tick={{ fontSize: 11, fill: "#4f7d71" }} tickLine={false} axisLine={false} />
                      <YAxis yAxisId="mean" tick={{ fontSize: 11, fill: "#4f7d71" }} tickLine={false} axisLine={false} unit="°C" />
                      <YAxis yAxisId="anomaly" orientation="right" tick={{ fontSize: 11, fill: "#6f9a8f" }} tickLine={false} axisLine={false} unit="°C" />
                      <Tooltip contentStyle={{ borderRadius: 12, borderColor: "#e3ebe8", fontSize: 12 }} />
                      <Bar yAxisId="anomaly" dataKey="anomaly" name="Anomaly (°C)" fill="#e9b76b" fillOpacity={0.75} />
                      <Line yAxisId="mean" type="monotone" dataKey="mean" name="Annual mean (°C)" stroke="#243733" strokeWidth={2.5} dot={false} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
                <p className="mt-3 text-xs leading-5 text-ink-500">
                  {tempTrend
                    ? `${tempTrend.method}. ${tempTrend.caveat}`
                    : "A trend is only fitted when at least five annual values are present."}
                </p>
              </div>
            ) : (
              <p className="prose-civic mt-4">No annual temperature series is available.</p>
            )}
          </section>

          <section className="grid gap-6 lg:grid-cols-2">
            <div>
              <SectionHeading
                eyebrow="Annual rainfall"
                title="Reanalysis total"
                action={rainTrend ? <span className="chip border-ink-200 bg-white text-ink-600">{formatNumber(rainTrend.slope_per_decade, 1)} mm/decade</span> : null}
              />
              {rainData.length ? (
                <div className="panel mt-4 p-4 sm:p-6">
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={rainData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                        <CartesianGrid stroke="#e3ebe8" strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="year" tick={{ fontSize: 10, fill: "#4f7d71" }} tickLine={false} axisLine={false} />
                        <YAxis tick={{ fontSize: 11, fill: "#4f7d71" }} tickLine={false} axisLine={false} unit="mm" />
                        <Tooltip contentStyle={{ borderRadius: 12, borderColor: "#e3ebe8", fontSize: 12 }} />
                        <Bar dataKey="value" name="Annual rainfall (mm)" fill="#6f9a8f" fillOpacity={0.8} radius={[3, 3, 0, 0]} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                  {rainTrend ? (
                    <p className="mt-3 text-xs leading-5 text-ink-500">
                      Descriptive OLS slope: {formatNumber(rainTrend.slope_per_decade, 2)} mm per decade
                      over {rainTrend.n_years} years. {rainTrend.caveat}
                    </p>
                  ) : (
                    <p className="mt-3 text-xs text-ink-500">Not enough annual values for a trend.</p>
                  )}
                </div>
              ) : (
                <p className="prose-civic mt-4">No annual rainfall series is available.</p>
              )}
            </div>

            <div>
              <SectionHeading eyebrow="Extreme-day counts" title="Hot days and heavy-rain days" />
              <div className="panel mt-4 p-4 sm:p-6">
                {hotDays.length || heavyRain.length ? (
                  <div className="space-y-6">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Days ≥ 35°C</p>
                      <div className="mt-2 h-28 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <ComposedChart data={hotDays} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
                            <XAxis dataKey="year" tick={{ fontSize: 9, fill: "#4f7d71" }} tickLine={false} axisLine={false} />
                            <YAxis tick={{ fontSize: 9, fill: "#4f7d71" }} tickLine={false} axisLine={false} />
                            <Tooltip contentStyle={{ borderRadius: 12, borderColor: "#e3ebe8", fontSize: 12 }} />
                            <Bar dataKey="value" name="Days" fill="#d97706" fillOpacity={0.8} />
                          </ComposedChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Days ≥ 50 mm rain</p>
                      <div className="mt-2 h-28 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <ComposedChart data={heavyRain} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
                            <XAxis dataKey="year" tick={{ fontSize: 9, fill: "#4f7d71" }} tickLine={false} axisLine={false} />
                            <YAxis tick={{ fontSize: 9, fill: "#4f7d71" }} tickLine={false} axisLine={false} />
                            <Tooltip contentStyle={{ borderRadius: 12, borderColor: "#e3ebe8", fontSize: 12 }} />
                            <Bar dataKey="value" name="Days" fill="#0f766e" fillOpacity={0.8} />
                          </ComposedChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-ink-600">No extreme-day series is available.</p>
                )}
              </div>
            </div>
          </section>

          {seasonal.seasons.length ? (
            <section>
              <SectionHeading
                eyebrow="Seasonal context"
                title="Mean temperature by season"
                description="DJF: Dec–Feb · MAM: Mar–May · JJA: Jun–Aug · SON: Sep–Nov. Seasonal aggregation can reveal patterns hidden by annual means."
              />
              <div className="panel mt-5 p-4 sm:p-6">
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={seasonal.data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                      <CartesianGrid stroke="#e3ebe8" strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="year" tick={{ fontSize: 10, fill: "#4f7d71" }} tickLine={false} axisLine={false} />
                      <YAxis tick={{ fontSize: 11, fill: "#4f7d71" }} tickLine={false} axisLine={false} unit="°C" />
                      <Tooltip contentStyle={{ borderRadius: 12, borderColor: "#e3ebe8", fontSize: 12 }} />
                      {seasonal.seasons.map((season) => (
                        <Line
                          key={season}
                          type="monotone"
                          dataKey={season}
                          name={season}
                          stroke={seasonColors[season] ?? "#243733"}
                          strokeWidth={2}
                          dot={false}
                        />
                      ))}
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-3 flex flex-wrap gap-4 text-xs text-ink-500">
                  {seasonal.seasons.map((season) => (
                    <span key={season} className="inline-flex items-center gap-1.5">
                      <span className="h-2 w-4 rounded-full" style={{ backgroundColor: seasonColors[season] ?? "#243733" }} />
                      {season}
                    </span>
                  ))}
                </div>
                {data.trends.seasonal_temperature ? (
                  <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                    {Object.entries(data.trends.seasonal_temperature).map(([season, trend]) => (
                      <div key={season} className="rounded-lg border border-ink-100 bg-ink-50 p-3 text-xs">
                        <p className="font-semibold text-ink-800">{season}</p>
                        <p className="mt-1 text-ink-600">
                          {trend ? `${formatNumber(trend.slope_per_decade, 2)}°C/decade` : "Insufficient years"}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            </section>
          ) : null}

          <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="panel p-5 sm:p-6">
              <p className="eyebrow">Methodology & caveats</p>
              <p className="prose-civic mt-3">{data.methodology}</p>
              <p className="mt-3 text-xs leading-5 text-amber-800">
                These series are reanalysis products, not thermometers in Kolkata. They are useful for
                broad context. They are not evidence about a specific neighbourhood, building or
                person&apos;s exposure.
              </p>
              {data.dataset ? (
                <p className="mt-3 text-xs text-ink-500">
                  Dataset: {data.dataset.name} · native resolution ~{Math.round(data.dataset.native_resolution_m / 1000)} km ·{" "}
                  {data.dataset.provider_access}. {data.dataset.note}
                </p>
              ) : null}
            </div>
            <div className="panel p-5 sm:p-6">
              <p className="eyebrow">Baselines</p>
              {data.baselines?.length ? (
                <ul className="mt-3 space-y-2 text-sm text-ink-700">
                  {data.baselines.map((baseline, index) => (
                    <li key={index} className="rounded-lg border border-ink-100 p-3">
                      <span className="font-medium">{String(baseline.name ?? "Baseline")}</span>
                      <span className="mt-1 block text-xs text-ink-500">
                        {String(baseline.start_year ?? "—")}–{String(baseline.end_year ?? "—")} ·{" "}
                        {String(baseline.variable ?? "variable")} ·{" "}
                        {baseline.value !== undefined && baseline.value !== null
                          ? `${formatNumber(Number(baseline.value), 2)} ${String(baseline.unit ?? "")}`
                          : "no value"}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="prose-civic mt-3">No baseline metadata is attached to these metrics.</p>
              )}
              <div className="mt-4 flex flex-wrap gap-2">
                <Link to="/heat" className="btn-secondary text-xs">Heat &amp; satellite</Link>
                <Link to="/rainfall" className="btn-secondary text-xs">Recent rainfall</Link>
                <Link to="/methodology" className="btn-ghost text-xs">Full methodology</Link>
              </div>
            </div>
          </section>

          <SourcePanel
            source={data.source}
            note={data.methodology}
            extra={
              <p className="text-xs leading-5 text-ink-500">
                Trends are ordinary-least-squares slopes on annual values. Short records and
                autocorrelation limit causal interpretation. {titleCase(data.state)} state indicates
                that at least one metric series is present.
              </p>
            }
          />
        </>
      )}
    </div>
  );
}
