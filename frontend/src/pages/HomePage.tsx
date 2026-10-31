import { Link } from "react-router-dom";

import { useLocationSearch, usePlaceStatus } from "../api/queries";
import { useTemperatureUnit } from "../auth/context";
import { placePath } from "../lib/place";
import { PlaceSearch } from "../components/place/PlaceSearch";
import { StateBadge } from "../components/ui/DataState";
import { ErrorState, LoadingPanel } from "../components/ui/Feedback";
import { SectionHeading } from "../components/ui/SectionHeading";
import { StatCard } from "../components/ui/StatCard";
import { formatNumber, formatRelative, formatTemperature, formatWithUnit, titleCase } from "../lib/format";

const STATUS_TONE = {
  attention: "border-red-200 bg-red-50/70",
  watch: "border-amber-200 bg-amber-50/70",
  typical: "border-emerald-200 bg-emerald-50/60",
  unknown: "border-ink-200 bg-ink-50/70",
} as const;

export function HomePage() {
  const unit = useTemperatureUnit();
  const place = usePlaceStatus();
  const localities = useLocationSearch("");
  const data = place.data;

  return (
    <div className="shell space-y-8 py-8 sm:py-12">
      <section className="panel overflow-hidden">
        <div className="grid gap-6 p-6 sm:p-9 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
          <div>
            <p className="eyebrow">Kolkata · area-first civic climate tool</p>
            <h1 className="display-title mt-3 max-w-2xl">
              Check your area before you head out.
            </h1>
            <p className="prose-civic mt-3 max-w-xl text-base">
              Search a neighbourhood to see rain, waterlogging signals, heat, air quality, official
              warnings and nearby community reports in one place.
            </p>
            <div className="mt-5 max-w-xl">
              <PlaceSearch size="lg" />
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="text-xs text-ink-500">Try:</span>
              {(localities.data?.results ?? []).slice(0, 6).map((locality) => (
                <Link
                  key={`${locality.type}-${locality.id}`}
                  to={placePath(locality)}
                  className="rounded-full border border-ink-200 bg-white px-2.5 py-1 text-xs font-medium text-ink-700 hover:border-ink-300"
                >
                  {locality.name}
                </Link>
              ))}
              {localities.isLoading ? <span className="text-xs text-ink-400">Loading localities…</span> : null}
            </div>
          </div>
          <div className="rounded-2xl border border-ink-100 bg-ink-50/60 p-4">
            <p className="eyebrow">What you get</p>
            <ul className="mt-3 space-y-2 text-sm leading-6 text-ink-700">
              <li>· One status for your area, not nine separate dashboards.</li>
              <li>· Clear labels for observed, forecast, rule-based and community data.</li>
              <li>· Honest unavailable states instead of made-up numbers.</li>
            </ul>
            <Link to="/methodology" className="mt-3 inline-block text-xs font-medium text-ink-700 underline">
              Read the data and method notes
            </Link>
          </div>
        </div>
      </section>

      <section>
        <SectionHeading
          eyebrow="Kolkata overview"
          title="The city right now"
          description="A compact snapshot from the same area-status service. Open the full page for inputs, caveats and nearby reports."
          action={
            <Link to="/place/kolkata" className="btn-secondary !px-3 !py-1.5 text-xs">
              Open Kolkata status
            </Link>
          }
        />

        {place.isError ? (
          <ErrorState className="mt-4" error={place.error} onRetry={() => void place.refetch()} />
        ) : place.isLoading || !data ? (
          <LoadingPanel label="Loading Kolkata status" rows={4} />
        ) : (
          <div className="mt-4 space-y-4">
            <div className={`rounded-2xl border p-5 ${STATUS_TONE[data.status.level]}`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-display text-xl text-ink-950">{data.status.headline}</h3>
                  <ul className="mt-2 space-y-1 text-sm leading-6 text-ink-700">
                    {data.status.reasons.slice(0, 3).map((reason) => (
                      <li key={reason}>· {reason}</li>
                    ))}
                  </ul>
                </div>
                <div className="flex flex-col items-start gap-1 sm:items-end">
                  <StateBadge state={data.status.state} />
                  <p className="text-xs text-ink-500">Updated {formatRelative(data.generated_at)}</p>
                </div>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard
                label="Waterlogging signal"
                value={data.waterlogging.label}
                detail={`${data.waterlogging.points}/${data.waterlogging.max_points} points · rule-based, not ML`}
                tone={data.waterlogging.level === "high" ? "alert" : data.waterlogging.level === "elevated" ? "warm" : "default"}
              />
              <StatCard
                label="Rain next 24 h"
                value={formatWithUnit(data.rain.next_24h_total_mm, "mm")}
                detail={
                  data.rain.next_24h_max_probability_pct === null
                    ? data.rain.reason ?? "Forecast unavailable"
                    : `${formatNumber(data.rain.next_24h_max_probability_pct)}% peak chance`
                }
              />
              <StatCard
                label="Heat stress"
                value={formatTemperature(data.heat.air.value_c, unit)}
                detail={data.heat.air.value_label ? titleCase(data.heat.air.value_label) : data.heat.air.reason ?? "Unavailable"}
                tone={data.heat.air.level === "warning" ? "alert" : data.heat.air.level === "caution" ? "warm" : "default"}
              />
              <StatCard
                label="Official alerts"
                value={data.alerts.count ? `${data.alerts.count} active` : "None in feed"}
                detail={data.alerts.count ? "Check the original bulletin" : data.alerts.reason ?? "No active warning"}
              />
            </div>

            <p className="text-xs leading-5 text-ink-500">
              {data.coverage.available} of {data.coverage.total} modules currently have a recent record. Air quality
              and satellite heat remain unavailable until provider credentials and real exports exist.
            </p>
          </div>
        )}
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <div className="panel p-5">
          <p className="eyebrow">1 · Search</p>
          <h2 className="mt-2 font-display text-lg text-ink-950">Start with your locality</h2>
          <p className="mt-2 text-sm leading-6 text-ink-600">
            Area status uses the Kolkata forecast point and reports within a 2.5 km neighbourhood radius or 5 km area
            radius. It is not a street-level sensor.
          </p>
        </div>
        <div className="panel p-5">
          <p className="eyebrow">2 · Check the signal</p>
          <h2 className="mt-2 font-display text-lg text-ink-950">Separate facts from signals</h2>
          <p className="mt-2 text-sm leading-6 text-ink-600">
            Observations, forecasts, rule-based indicators and resident reports are labelled separately. A low
            waterlogging signal is not a guarantee that a street is dry.
          </p>
        </div>
        <div className="panel p-5">
          <p className="eyebrow">3 · Add local evidence</p>
          <h2 className="mt-2 font-display text-lg text-ink-950">Report what you see</h2>
          <p className="mt-2 text-sm leading-6 text-ink-600">
            A photo and location help moderators verify waterlogging. Unverified reports are shown as unverified and
            never presented as official warnings.
          </p>
          <Link to="/reports/new" className="btn-primary mt-3 !px-3 !py-1.5 text-xs">
            Report an issue
          </Link>
        </div>
      </section>
    </div>
  );
}
