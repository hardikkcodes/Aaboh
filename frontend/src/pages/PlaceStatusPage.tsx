import { Link, useParams } from "react-router-dom";

import { usePlaceStatus } from "../api/queries";
import type {
  DataState,
  PlaceRiskLevel,
  PlaceSignalLevel,
  PlaceStatusLevel,
} from "../api/types";
import { useTemperatureUnit } from "../auth/context";
import { PlaceSearch } from "../components/place/PlaceSearch";
import { StateBadge } from "../components/ui/DataState";
import { ErrorState, LoadingPanel } from "../components/ui/Feedback";
import { SectionHeading } from "../components/ui/SectionHeading";
import { StatCard } from "../components/ui/StatCard";
import {
  formatDateTime,
  formatNumber,
  formatRelative,
  formatTemperature,
  formatWithUnit,
  titleCase,
  truncate,
} from "../lib/format";

const STATUS_TONE: Record<PlaceStatusLevel, { panel: string; chip: string; label: string }> = {
  attention: {
    panel: "border-red-200 bg-red-50/70",
    chip: "border-red-200 bg-red-100 text-red-900",
    label: "Needs attention",
  },
  watch: {
    panel: "border-amber-200 bg-amber-50/70",
    chip: "border-amber-200 bg-amber-100 text-amber-900",
    label: "Watch",
  },
  typical: {
    panel: "border-emerald-200 bg-emerald-50/60",
    chip: "border-emerald-200 bg-emerald-100 text-emerald-900",
    label: "No strong signal",
  },
  unknown: {
    panel: "border-ink-200 bg-ink-50/70",
    chip: "border-ink-200 bg-ink-100 text-ink-800",
    label: "Unavailable",
  },
};

const RISK_TONE: Record<PlaceRiskLevel, { chip: string; bar: string }> = {
  high: { chip: "border-red-200 bg-red-50 text-red-800", bar: "bg-red-500" },
  elevated: { chip: "border-amber-200 bg-amber-50 text-amber-800", bar: "bg-amber-500" },
  low: { chip: "border-emerald-200 bg-emerald-50 text-emerald-800", bar: "bg-emerald-500" },
  reports_only: { chip: "border-sky-200 bg-sky-50 text-sky-800", bar: "bg-sky-500" },
  unknown: { chip: "border-ink-200 bg-ink-50 text-ink-700", bar: "bg-ink-300" },
};

const SIGNAL_TONE: Record<PlaceSignalLevel, string> = {
  warning: "border-red-200 bg-red-50 text-red-800",
  caution: "border-amber-200 bg-amber-50 text-amber-800",
  info: "border-sky-200 bg-sky-50 text-sky-800",
  typical: "border-emerald-200 bg-emerald-50 text-emerald-800",
  unknown: "border-ink-200 bg-ink-50 text-ink-700",
};

function SignalChip({ level, label }: { level: PlaceSignalLevel; label: string }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium ${SIGNAL_TONE[level]}`}>
      {label}
    </span>
  );
}

function ModuleNote({ state, reason }: { state: DataState; reason?: string | null }) {
  if (state === "AVAILABLE") return null;
  return <p className="mt-2 text-xs leading-5 text-ink-500">{reason || "No recent record is available for this module."}</p>;
}

export function PlaceStatusPage() {
  const { areaSlug = "kolkata", neighbourhoodSlug } = useParams();
  const unit = useTemperatureUnit();
  const query = usePlaceStatus(areaSlug, neighbourhoodSlug);
  const data = query.data;

  if (query.isError) {
    return (
      <div className="shell py-12">
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      </div>
    );
  }

  if (query.isLoading || !data) {
    return (
      <div className="shell py-12">
        <LoadingPanel label="Loading area status" rows={5} />
      </div>
    );
  }

  const status = data.status;
  const tone = STATUS_TONE[status.level];
  const water = data.waterlogging;
  const risk = RISK_TONE[water.level];
  const current = data.weather.record;
  const reportQuery = new URLSearchParams({
    area: data.place.area.slug,
    name: data.place.neighbourhood?.name ?? data.place.area.name,
  });

  return (
    <div className="shell space-y-8 py-8 sm:py-10">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="eyebrow">Area status · Kolkata</p>
          <h1 className="display-title mt-2">{data.place.label}</h1>
          <p className="prose-civic mt-2 max-w-2xl">{data.place.scope_note}</p>
        </div>
        <div className="w-full max-w-sm">
          <PlaceSearch />
          <p className="mt-2 text-xs text-ink-500">Search another area or neighbourhood to compare.</p>
        </div>
      </div>

      <section className={`rounded-2xl border p-5 sm:p-6 ${tone.panel}`}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-2xl">
            <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${tone.chip}`}>
              {tone.label}
            </span>
            <h2 className="mt-3 font-display text-2xl text-ink-950 sm:text-3xl">{status.headline}</h2>
            <ul className="mt-3 space-y-1.5 text-sm leading-6 text-ink-700">
              {status.reasons.map((reason) => (
                <li key={reason}>· {reason}</li>
              ))}
            </ul>
          </div>
          <div className="flex flex-col items-start gap-2 sm:items-end">
            <StateBadge state={status.state} />
            <p className="text-xs text-ink-500">
              Updated {formatRelative(data.generated_at)} · {formatDateTime(data.generated_at)}
            </p>
            <div className="flex flex-wrap gap-2">
              <Link to={`/reports?${reportQuery.toString()}`} className="btn-secondary !px-3 !py-1.5 text-xs">
                Community reports
              </Link>
              <Link to="/reports/new" className="btn-primary !px-3 !py-1.5 text-xs">
                Report an issue
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Waterlogging signal"
          value={water.label}
          detail={`${water.points} of ${water.max_points} points · ${water.reports.verified} verified / ${water.reports.unverified} unverified reports nearby`}
          tone={water.level === "high" ? "alert" : water.level === "elevated" ? "warm" : "default"}
        />
        <StatCard
          label="Rain next 24 h"
          value={formatWithUnit(data.rain.next_24h_total_mm, "mm")}
          detail={
            data.rain.next_24h_max_probability_pct === null
              ? data.rain.reason ?? "Forecast unavailable"
              : `Peak ${formatWithUnit(data.rain.peak_hour_mm, "mm")} around ${formatDateTime(data.rain.peak_hour)} · ${formatNumber(data.rain.next_24h_max_probability_pct)}% chance`
          }
        />
        <StatCard
          label="Heat stress"
          value={formatTemperature(data.heat.air.value_c, unit)}
          detail={
            data.heat.air.value_label
              ? `${titleCase(data.heat.air.value_label)} · ${titleCase(data.heat.air.level)} band`
              : data.heat.air.reason ?? "No current temperature record"
          }
          tone={data.heat.air.level === "warning" ? "alert" : data.heat.air.level === "caution" ? "warm" : "default"}
        />
        <StatCard
          label="Nearest CPCB station"
          value={data.air_quality.measurement?.aqi ? `AQI ${data.air_quality.measurement.aqi}` : "Unavailable"}
          detail={
            data.air_quality.measurement
              ? `${data.air_quality.measurement.aqi_category} · ${data.air_quality.station?.name ?? "Station"} · ${formatRelative(data.air_quality.measurement.measured_at)}`
              : data.air_quality.reason ?? "No station measurement nearby"
          }
          tone={data.air_quality.level === "warning" ? "alert" : data.air_quality.level === "caution" ? "warm" : "default"}
        />
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="panel p-5 sm:p-6">
          <SectionHeading
            eyebrow="Decision support · not a forecast"
            title={water.label}
            description={water.method.description}
            action={
              <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${risk.chip}`}>
                {water.points}/{water.max_points} points
              </span>
            }
          />

          <div className="mt-4 h-2 overflow-hidden rounded-full bg-ink-100" aria-hidden="true">
            <div className={`h-full ${risk.bar}`} style={{ width: `${(water.points / water.max_points) * 100}%` }} />
          </div>

          <dl className="mt-5 space-y-3">
            {water.inputs.map((input) => (
              <div key={input.key} className="flex items-start justify-between gap-4 border-b border-ink-100 pb-3 last:border-0 last:pb-0">
                <div>
                  <dt className="text-sm font-medium text-ink-900">{input.label}</dt>
                  <dd className="text-xs leading-5 text-ink-500">{input.detail}</dd>
                </div>
                <div className="shrink-0 text-right">
                  <span className="block text-sm font-semibold text-ink-900">
                    {formatWithUnit(input.value, input.unit, input.unit === "reports" ? 0 : 1)}
                  </span>
                  <span className="text-xs text-ink-500">+{input.contribution} point(s)</span>
                </div>
              </div>
            ))}
          </dl>

          <p className="mt-4 text-xs leading-5 text-ink-500">
            {water.reports.verified} verified and {water.reports.unverified} unverified water-related report(s) within{" "}
            {water.reports.radius_km} km in the last {water.reports.window_hours} hours.
          </p>

          <details className="mt-4 rounded-xl border border-ink-100 bg-ink-50/60 p-3">
            <summary className="cursor-pointer text-xs font-semibold text-ink-700">
              What this signal is not
            </summary>
            <ul className="mt-2 space-y-1.5 text-xs leading-5 text-ink-600">
              {water.caveats.map((caveat) => (
                <li key={caveat}>· {caveat}</li>
              ))}
            </ul>
          </details>
        </div>

        <div className="space-y-4">
          <div className="panel p-5">
            <SectionHeading eyebrow="Right now" title="Weather at the area forecast point" />
            {current ? (
              <div className="mt-4 space-y-3 text-sm text-ink-700">
                <p className="font-display text-3xl text-ink-950">
                  {formatTemperature(current.temperature_c, unit)}
                  {current.condition ? <span className="ml-3 text-base font-sans text-ink-600">{current.condition.label}</span> : null}
                </p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <span>Feels like {formatTemperature(current.apparent_temperature_c, unit)}</span>
                  <span>Humidity {formatNumber(current.relative_humidity)}%</span>
                  <span>Wind {formatWithUnit(current.wind_speed_kmh, "km/h")}</span>
                  <span>Rain {formatWithUnit(current.precipitation_mm, "mm")}</span>
                </div>
                <p className="text-xs text-ink-500">
                  Retrieved {formatRelative(current.retrieved_at)}. {data.weather.note}
                </p>
              </div>
            ) : (
              <p className="mt-4 text-sm text-ink-600">{data.weather.reason}</p>
            )}
            <div className="mt-3 flex flex-wrap gap-2">
              <StateBadge state={data.weather.state} />
              <Link to="/weather" className="btn-ghost !px-2 !py-1 text-xs">
                Full forecast
              </Link>
            </div>
          </div>

          <div className="panel p-5">
            <SectionHeading eyebrow="Heat" title="Air and surface heat" />
            <div className="mt-3 space-y-3 text-sm">
              <div>
                <p className="font-medium text-ink-900">Air</p>
                <p className="text-xs leading-5 text-ink-600">
                  {formatTemperature(data.heat.air.value_c, unit)} · {titleCase(data.heat.air.level)}. {data.heat.air.note}
                </p>
              </div>
              <div>
                <p className="font-medium text-ink-900">Land surface</p>
                <p className="text-xs leading-5 text-ink-600">
                  {data.heat.land_surface.nearest_cell_lst_c !== null
                    ? `${formatTemperature(data.heat.land_surface.nearest_cell_lst_c, unit)} at ${data.heat.land_surface.nearest_cell_code} · scene ${data.heat.land_surface.latest_date}`
                    : data.heat.land_surface.reason ?? data.heat.land_surface.note}
                </p>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <SignalChip level={data.heat.air.level} label={`Air: ${titleCase(data.heat.air.level)}`} />
              <StateBadge state={data.heat.land_surface.state} />
              <Link to="/heat" className="btn-ghost !px-2 !py-1 text-xs">
                Heat &amp; environment
              </Link>
            </div>
          </div>

          <div className="panel p-5">
            <SectionHeading eyebrow="Official alerts" title="Source-issued warnings" />
            <ModuleNote state={data.alerts.state} reason={data.alerts.reason} />
            {data.alerts.results.length ? (
              <ul className="mt-3 space-y-2">
                {data.alerts.results.map((alert) => (
                  <li key={alert.id} className="rounded-xl border border-ink-100 p-3">
                    <p className="text-sm font-medium text-ink-900">{alert.title}</p>
                    <p className="mt-1 text-xs text-ink-500">
                      {alert.hazard_label} · {alert.severity_label} · issued {formatRelative(alert.issued_at)}
                    </p>
                  </li>
                ))}
              </ul>
            ) : null}
            <div className="mt-3 flex flex-wrap gap-2">
              <StateBadge state={data.alerts.state} />
              <Link to="/alerts" className="btn-ghost !px-2 !py-1 text-xs">
                All official alerts
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1fr_0.8fr]">
        <div className="panel p-5 sm:p-6">
          <SectionHeading
            eyebrow={`${data.reports.radius_km} km · last ${data.reports.window_hours} h`}
            title="Nearby community reports"
            description={data.reports.note}
            action={
              <Link to={`/reports?${reportQuery.toString()}`} className="btn-secondary !px-3 !py-1.5 text-xs">
                Open reports
              </Link>
            }
          />
          {data.reports.results.length ? (
            <ul className="mt-4 space-y-2">
              {data.reports.results.map((report) => (
                <li key={report.id}>
                  <Link
                    to={`/reports/${report.id}`}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-ink-100 p-3 transition hover:border-ink-200 hover:bg-ink-50/50"
                  >
                    <span>
                      <span className="block text-sm font-medium text-ink-900">{report.category_label}</span>
                      <span className="text-xs text-ink-500">
                        {truncate(report.description, 90)}
                      </span>
                    </span>
                    <span className="flex items-center gap-2 text-xs">
                      <span
                        className={`rounded-full border px-2 py-0.5 font-medium ${
                          report.verification_state === "VERIFIED"
                            ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                            : "border-amber-200 bg-amber-50 text-amber-800"
                        }`}
                      >
                        {report.verification_state === "VERIFIED" ? "Verified" : "Unverified"}
                      </span>
                      <span className="text-ink-500">{formatRelative(report.occurred_at)}</span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm text-ink-600">{data.reports.reason}</p>
          )}
        </div>

        <div className="panel p-5 sm:p-6">
          <SectionHeading eyebrow="Coverage" title="What exists for this place" />
          <p className="mt-2 text-xs leading-5 text-ink-500">
            {data.coverage.available} of {data.coverage.total} modules have a recent record. Unavailable modules are
            shown as missing, never filled with invented values.
          </p>
          <ul className="mt-4 space-y-2">
            {data.coverage.modules.map((module) => (
              <li key={module.key} className="flex items-center justify-between gap-3 rounded-xl border border-ink-100 px-3 py-2">
                <span className="text-sm text-ink-700">{module.label}</span>
                <StateBadge state={module.state} />
              </li>
            ))}
          </ul>
          <p className="mt-4 text-xs leading-5 text-ink-500">{data.disclaimer}</p>
          <Link to="/methodology" className="mt-2 inline-block text-xs font-medium text-ink-700 underline">
            How this is calculated
          </Link>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <div className="panel p-4">
          <p className="eyebrow">Rain in the last 48 h</p>
          <p className="mt-2 text-sm text-ink-800">
            {data.recent_rain.max_daily_mm === null
              ? "No recent daily rainfall records"
              : `Highest day ${formatWithUnit(data.recent_rain.max_daily_mm, "mm")} · total ${formatWithUnit(data.recent_rain.total_mm, "mm")} across ${data.recent_rain.days_covered} day(s)`}
          </p>
          <p className="mt-1 text-xs leading-5 text-ink-500">{data.recent_rain.note}</p>
        </div>
        <div className="panel p-4">
          <p className="eyebrow">Air quality basis</p>
          <p className="mt-2 text-sm text-ink-800">
            {data.air_quality.station
              ? `${data.air_quality.station.name} · ${formatNumber(data.air_quality.distance_km, 1)} km away`
              : "No CPCB station within 75 km"}
          </p>
          <p className="mt-1 text-xs leading-5 text-ink-500">{data.air_quality.note}</p>
        </div>
        <div className="panel p-4">
          <p className="eyebrow">Official warning check</p>
          <p className="mt-2 text-sm text-ink-800">
            {data.alerts.count ? `${data.alerts.count} active warning(s)` : "No active warning in the stored feed"}
          </p>
          <p className="mt-1 text-xs leading-5 text-ink-500">{data.alerts.note}</p>
        </div>
      </section>
    </div>
  );
}
