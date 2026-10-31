import {
  CartesianGrid,
  ComposedChart,
  Line,
  Area,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Link } from "react-router-dom";

import { useWeatherCurrent, useWeatherForecast, useWeatherHistory } from "../api/queries";
import type { WeatherRecord } from "../api/types";
import { useTemperatureUnit } from "../auth/context";
import { DataStateNotice, StateBadge } from "../components/ui/DataState";
import { ErrorState, LoadingPanel } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";
import { SectionHeading } from "../components/ui/SectionHeading";
import { SourcePanel } from "../components/ui/SourcePanel";
import {
  formatDateTime,
  formatDay,
  formatHour,
  formatPercent,
  formatRelative,
  formatTemperature,
  formatTime,
  formatWithUnit,
} from "../lib/format";

function Detail({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-ink-100 bg-white p-4">
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-ink-500">{label}</p>
      <p className="mt-1.5 text-lg font-semibold text-ink-950">{value}</p>
      {hint ? <p className="mt-1 text-[0.68rem] leading-4 text-ink-400">{hint}</p> : null}
    </div>
  );
}

function hourlySeries(records: WeatherRecord[], unit: "C" | "F") {
  return records.map((record) => ({
    label: formatHour(record.valid_time),
    time: formatTime(record.valid_time),
    temperature: record.temperature_c === null ? null : unit === "F" ? record.temperature_c * 1.8 + 32 : record.temperature_c,
    apparent: record.apparent_temperature_c === null ? null : unit === "F" ? record.apparent_temperature_c * 1.8 + 32 : record.apparent_temperature_c,
    rain: record.precipitation_mm,
    probability: record.precipitation_probability,
  }));
}

function historySeries(records: WeatherRecord[], unit: "C" | "F") {
  const convert = (value: number | null) =>
    value === null ? null : unit === "F" ? value * 1.8 + 32 : value;
  return records.map((record) => ({
    label: formatDay(record.valid_time),
    max: convert(record.temperature_max_c),
    min: convert(record.temperature_min_c),
    rain: record.precipitation_mm,
  }));
}

export function WeatherPage() {
  const unit = useTemperatureUnit();
  const current = useWeatherCurrent();
  const forecast = useWeatherForecast();
  const history = useWeatherHistory(undefined, 90);

  const record = current.data?.record;
  const hourly = forecast.data?.hourly ?? [];
  const daily = forecast.data?.daily ?? [];
  const historyData = historySeries(history.data?.daily ?? [], unit);

  return (
    <div className="shell space-y-10 py-10 sm:py-14">
      <PageHeader
        eyebrow="Weather · Kolkata"
        title="Forecast, current conditions and recent history"
        description="Provider forecast and reanalysis data, shown separately from official warnings and station observations. Times are IST."
        aside={current.data ? <StateBadge state={current.data.state} /> : null}
      />

      {current.isError ? (
        <ErrorState error={current.error} onRetry={() => void current.refetch()} />
      ) : current.isLoading ? (
        <LoadingPanel label="Loading current conditions" rows={2} />
      ) : record ? (
        <section className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="relative overflow-hidden rounded-3xl border border-ink-100 bg-ink-950 p-6 text-white shadow-panel sm:p-8">
            <div className="pointer-events-none absolute inset-0 opacity-30 [background:radial-gradient(circle_at_80%_10%,rgba(224,154,66,0.6),transparent_45%)]" />
            <div className="relative">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-xs font-semibold uppercase tracking-[0.17em] text-ink-200">Current conditions</p>
                <StateBadge state={current.data?.state ?? "UNAVAILABLE"} />
              </div>
              <div className="mt-5 flex flex-wrap items-end gap-4">
                <p className="font-display text-6xl leading-none sm:text-7xl">
                  {formatTemperature(record.temperature_c, unit, 0)}
                </p>
                <div className="pb-1">
                  <p className="text-xl font-medium">{record.condition?.label ?? "Conditions reported"}</p>
                  <p className="mt-1 text-sm text-ink-200">
                    Feels like {formatTemperature(record.apparent_temperature_c, unit)}
                  </p>
                </div>
              </div>
              <div className="mt-6 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
                {[
                  { label: "Humidity", value: formatPercent(record.relative_humidity) },
                  { label: "Wind", value: formatWithUnit(record.wind_speed_kmh, "km/h", 0) },
                  { label: "Gusts", value: formatWithUnit(record.wind_gust_kmh, "km/h", 0) },
                  { label: "Cloud", value: formatPercent(record.cloud_cover) },
                  { label: "Rain", value: formatWithUnit(record.precipitation_mm, "mm", 1) },
                  { label: "Pressure", value: formatWithUnit(record.pressure_hpa, "hPa", 0) },
                  { label: "Visibility", value: formatWithUnit(record.visibility_m ? record.visibility_m / 1000 : null, "km", 1) },
                  { label: "Dew point", value: formatTemperature(record.dew_point_c, unit) },
                ].map((item) => (
                  <div key={item.label} className="rounded-xl bg-white/10 p-3">
                    <p className="text-[0.62rem] uppercase tracking-wide text-ink-300">{item.label}</p>
                    <p className="mt-1 font-medium">{item.value}</p>
                  </div>
                ))}
              </div>
              <p className="mt-5 text-xs leading-5 text-ink-200">
                Observed for {formatDateTime(current.data?.observed_at)} · retrieved{" "}
                {formatRelative(current.data?.retrieved_at)}. {current.data?.note}
              </p>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <Detail label="Forecast state" value={forecast.data ? forecast.data.state.replaceAll("_", " ") : "—"} hint="Provider forecast pipeline" />
            <Detail label="Next high" value={formatTemperature(daily[0]?.temperature_max_c, unit)} hint="Daily provider forecast" />
            <Detail label="Next low" value={formatTemperature(daily[0]?.temperature_min_c, unit)} hint="Daily provider forecast" />
            <Detail
              label="Rain probability"
              value={formatPercent(hourly[0]?.precipitation_probability)}
              hint="First forecast hour"
            />
            <Detail
              label="Sunrise / sunset"
              value="—"
              hint="Not exposed by this API response"
            />
            <Detail
              label="Official warning"
              value="Separate layer"
              hint="Forecasts are never treated as official warnings"
            />
            <Link to="/alerts" className="btn-secondary sm:col-span-2">
              Check official IMD alerts
            </Link>
          </div>
        </section>
      ) : (
        <div className="panel-muted p-6">
          <p className="font-display text-xl text-ink-900">No current weather record is available</p>
          <p className="prose-civic mt-2">
            Nothing has been substituted. The forecast and historical endpoints below may still have data.
          </p>
        </div>
      )}

      {current.data ? (
        <DataStateNotice state={current.data.state} reason={current.data.note} />
      ) : null}

      <section>
        <SectionHeading
          eyebrow="Next 48 hours"
          title="Hourly forecast"
          description="Temperature lines use the selected unit. Rainfall bars are provider forecast values, not a waterlogging prediction."
          action={forecast.data ? <StateBadge state={forecast.data.state} /> : null}
        />
        {forecast.isError ? (
          <ErrorState className="mt-5" error={forecast.error} onRetry={() => void forecast.refetch()} />
        ) : forecast.isLoading ? (
          <div className="mt-5"><LoadingPanel label="Loading hourly forecast" /></div>
        ) : hourly.length ? (
          <div className="panel mt-5 p-4 sm:p-6">
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={hourlySeries(hourly, unit)} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                  <CartesianGrid stroke="#e3ebe8" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#4f7d71" }} interval={5} tickLine={false} axisLine={false} />
                  <YAxis yAxisId="temp" tick={{ fontSize: 11, fill: "#4f7d71" }} tickLine={false} axisLine={false} unit={`°${unit}`} />
                  <YAxis yAxisId="rain" orientation="right" tick={{ fontSize: 11, fill: "#6f9a8f" }} tickLine={false} axisLine={false} unit="mm" />
                  <Tooltip contentStyle={{ borderRadius: 12, borderColor: "#e3ebe8", fontSize: 12 }} />
                  <Area yAxisId="rain" type="monotone" dataKey="rain" name="Rain (mm)" fill="#c8d8d3" stroke="#6f9a8f" fillOpacity={0.5} />
                  <Line yAxisId="temp" type="monotone" dataKey="temperature" name={`Temperature (°${unit})`} stroke="#bb621b" strokeWidth={2.5} dot={false} />
                  <Line yAxisId="temp" type="monotone" dataKey="apparent" name={`Feels like (°${unit})`} stroke="#9fbdb4" strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 flex flex-wrap gap-4 text-xs text-ink-500">
              <span className="inline-flex items-center gap-1.5"><span className="h-2 w-4 rounded-full bg-ember-600" /> Temperature</span>
              <span className="inline-flex items-center gap-1.5"><span className="h-2 w-4 rounded-full bg-ink-300" /> Feels like</span>
              <span className="inline-flex items-center gap-1.5"><span className="h-2 w-4 rounded-full bg-ink-200" /> Rain (mm)</span>
            </div>
            <p className="mt-3 text-xs text-ink-500">{forecast.data?.note}</p>
          </div>
        ) : (
          <div className="panel-muted mt-5 p-5">
            <p className="text-sm font-medium text-ink-800">No hourly forecast rows are stored</p>
            <p className="mt-1 text-xs leading-5 text-ink-500">
              {forecast.data?.note ?? "The weather ingestion pipeline may not have run."}
            </p>
          </div>
        )}
      </section>

      <section>
        <SectionHeading eyebrow="Seven days" title="Daily outlook" />
        {daily.length ? (
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
            {daily.slice(0, 7).map((day) => (
              <div key={day.id} className="panel p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">{formatDay(day.valid_time)}</p>
                <p className="mt-2 text-sm font-medium text-ink-900">{day.condition?.label ?? "—"}</p>
                <p className="mt-2 font-display text-2xl text-ink-950">
                  {formatTemperature(day.temperature_max_c, unit, 0)}
                </p>
                <p className="text-xs text-ink-500">
                  Low {formatTemperature(day.temperature_min_c, unit, 0)}
                </p>
                <p className="mt-2 text-xs text-ink-500">
                  Rain {formatWithUnit(day.precipitation_mm, "mm", 1)}
                  {day.precipitation_probability !== null ? ` · ${formatPercent(day.precipitation_probability)}` : ""}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="prose-civic mt-4">No daily forecast rows are available.</p>
        )}
        {forecast.data ? (
          <DataStateNotice className="mt-4" state={forecast.data.state} reason={forecast.data.note} />
        ) : null}
      </section>

      <section>
        <SectionHeading
          eyebrow="Previous 90 days"
          title="Recent temperature history"
          description="ERA5-Land daily reanalysis (~9 km), not a neighbourhood station record."
          action={history.data ? <StateBadge state={history.data.state} /> : null}
        />
        {history.isError ? (
          <ErrorState className="mt-5" error={history.error} onRetry={() => void history.refetch()} />
        ) : history.isLoading ? (
          <div className="mt-5"><LoadingPanel label="Loading weather history" /></div>
        ) : historyData.length ? (
          <div className="panel mt-5 p-4 sm:p-6">
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={historyData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                  <CartesianGrid stroke="#e3ebe8" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 10, fill: "#4f7d71" }} minTickGap={45} tickLine={false} axisLine={false} />
                  <YAxis yAxisId="temp" tick={{ fontSize: 11, fill: "#4f7d71" }} tickLine={false} axisLine={false} unit={`°${unit}`} />
                  <YAxis yAxisId="rain" orientation="right" tick={{ fontSize: 11, fill: "#6f9a8f" }} tickLine={false} axisLine={false} unit="mm" />
                  <Tooltip contentStyle={{ borderRadius: 12, borderColor: "#e3ebe8", fontSize: 12 }} />
                  <Area yAxisId="rain" type="monotone" dataKey="rain" name="Rain (mm)" fill="#e3ebe8" stroke="#9fbdb4" fillOpacity={0.6} />
                  <Line yAxisId="temp" type="monotone" dataKey="max" name={`Daily max (°${unit})`} stroke="#bb621b" strokeWidth={2} dot={false} />
                  <Line yAxisId="temp" type="monotone" dataKey="min" name={`Daily min (°${unit})`} stroke="#325149" strokeWidth={2} dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-3 flex flex-wrap gap-4 text-xs text-ink-500">
              <span className="inline-flex items-center gap-1.5"><span className="h-2 w-4 rounded-full bg-ember-600" /> Daily maximum</span>
              <span className="inline-flex items-center gap-1.5"><span className="h-2 w-4 rounded-full bg-ink-700" /> Daily minimum</span>
              <span className="inline-flex items-center gap-1.5"><span className="h-2 w-4 rounded-full bg-ink-200" /> Daily rainfall</span>
            </div>
            <p className="mt-3 text-xs text-ink-500">{history.data?.note}</p>
          </div>
        ) : (
          <div className="panel-muted mt-5 p-5">
            <p className="text-sm font-medium text-ink-800">No historical weather rows in this window</p>
            <p className="mt-1 text-xs text-ink-500">Run the weather-history ingestion to populate this series.</p>
          </div>
        )}
      </section>

      <SourcePanel
        source={forecast.data?.source ?? current.data?.source ?? history.data?.source}
        retrievedAt={forecast.data?.retrieved_at ?? current.data?.retrieved_at}
        note={forecast.data?.note ?? current.data?.note}
        extra={
          <p className="text-xs leading-5 text-ink-500">
            Daily history is aggregated reanalysis from ERA5-Land via Open-Meteo (~9 km). Current
            conditions are a provider analysis/forecast point and are not station measurements.{" "}
            <Link className="link" to="/methodology">Read the methodology</Link>.
          </p>
        }
      />
    </div>
  );
}
