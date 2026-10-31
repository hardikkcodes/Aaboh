import { Link } from "react-router-dom";

import {
  useAirStations,
  useAlerts,
  useClimateTrends,
  useDataStatus,
  useHeatHotspots,
  useIncidents,
  useIncidentSummary,
  useInsights,
  useRainfallForecast,
  useWeatherCurrent,
} from "../api/queries";
import { useTemperatureUnit } from "../auth/context";
import { InsightCard } from "../components/insights/InsightCard";
import { DataStateNotice, StateBadge } from "../components/ui/DataState";
import { ErrorState, LoadingPanel } from "../components/ui/Feedback";
import { SectionHeading } from "../components/ui/SectionHeading";
import { StatCard } from "../components/ui/StatCard";
import { MODULE_LABELS, MODULE_LINKS } from "../lib/constants";
import {
  formatDateTime,
  formatNumber,
  formatPercent,
  formatRelative,
  formatTemperature,
  formatWithUnit,
  titleCase,
  truncate,
} from "../lib/format";

export function HomePage() {
  const unit = useTemperatureUnit();
  const status = useDataStatus();
  const current = useWeatherCurrent();
  const insights = useInsights();
  const alerts = useAlerts();
  const rainfall = useRainfallForecast();
  const air = useAirStations();
  const heat = useHeatHotspots();
  const climate = useClimateTrends();
  const summary = useIncidentSummary();
  const incidents = useIncidents({ since_hours: 24 * 7 });

  const currentRecord = current.data?.record;
  const moduleEntries = status.data ? Object.entries(status.data.modules) : [];
  const availableCount = moduleEntries.filter(([, module]) => module.state === "AVAILABLE").length;
  const substantiveInsights =
    insights.data?.insights.filter((insight) => insight.kind !== "data_availability") ?? [];
  const visibleInsights = substantiveInsights.slice(0, 3);

  return (
    <div>
      <section className="relative overflow-hidden border-b border-ink-100 bg-gradient-to-br from-ink-950 via-ink-900 to-ink-800 text-white">
        <div className="pointer-events-none absolute inset-0 opacity-30 [background:radial-gradient(circle_at_20%_20%,rgba(224,154,66,0.55),transparent_35%),radial-gradient(circle_at_80%_0%,rgba(111,154,143,0.5),transparent_40%)]" />
        <div className="shell relative grid gap-10 py-14 lg:grid-cols-[1.25fr_0.9fr] lg:py-20">
          <div className="max-w-2xl">
            <p className="text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-ember-200">
              Kolkata · civic climate intelligence
            </p>
            <h1 className="mt-4 font-display text-4xl leading-[1.05] sm:text-5xl lg:text-6xl">
              The city&apos;s climate, with its receipts.
            </h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-ink-100">
              Weather forecasts, official warnings, satellite heat, rainfall, air quality and resident
              reports in one place — each with its source, timestamp, units and quality. When a layer is
              missing, we show the gap rather than invent a number.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link to="/insights" className="btn bg-ember-400 text-ink-950 hover:bg-ember-300">
                Read today&apos;s briefing
              </Link>
              <Link to="/reports/new" className="btn border-white/25 bg-white/10 text-white hover:bg-white/20">
                Report a local issue
              </Link>
              <Link to="/methodology" className="btn text-ink-100 hover:bg-white/10">
                How the data works
              </Link>
            </div>
            <div className="mt-8 flex flex-wrap gap-x-8 gap-y-3 text-xs text-ink-200">
              <span><strong className="text-white">{availableCount}/6</strong> public layers reporting</span>
              <span><strong className="text-white">{summary.data?.total ?? "—"}</strong> community reports this week</span>
              <span>All times shown in IST</span>
            </div>
          </div>

          <div className="self-start rounded-3xl border border-white/15 bg-white/10 p-5 backdrop-blur-md sm:p-6">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-ink-100">Right now</p>
              {current.data ? <StateBadge state={current.data.state} /> : null}
            </div>
            {current.isLoading ? (
              <div className="mt-6 space-y-3">
                <div className="h-16 w-36 animate-pulse rounded-xl bg-white/15" />
                <div className="h-4 w-48 animate-pulse rounded-full bg-white/10" />
              </div>
            ) : current.isError ? (
              <p className="mt-6 text-sm leading-6 text-ember-100">
                The weather endpoint could not be reached. Other layers are still shown separately.
              </p>
            ) : currentRecord ? (
              <>
                <div className="mt-4 flex items-end gap-3">
                  <p className="font-display text-6xl leading-none">
                    {formatTemperature(currentRecord.temperature_c, unit, 0)}
                  </p>
                  <div className="pb-1">
                    <p className="text-lg font-medium">{currentRecord.condition?.label ?? titleCase(currentRecord.quality_status)}</p>
                    <p className="mt-1 text-xs text-ink-200">
                      Feels {formatTemperature(currentRecord.apparent_temperature_c, unit, 0)}
                    </p>
                  </div>
                </div>
                <dl className="mt-6 grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-xl bg-black/15 p-3">
                    <dt className="text-[0.65rem] uppercase tracking-wide text-ink-300">Humidity</dt>
                    <dd className="mt-1 font-medium">{formatPercent(currentRecord.relative_humidity)}</dd>
                  </div>
                  <div className="rounded-xl bg-black/15 p-3">
                    <dt className="text-[0.65rem] uppercase tracking-wide text-ink-300">Wind</dt>
                    <dd className="mt-1 font-medium">
                      {formatWithUnit(currentRecord.wind_speed_kmh, "km/h", 0)}
                    </dd>
                  </div>
                  <div className="rounded-xl bg-black/15 p-3">
                    <dt className="text-[0.65rem] uppercase tracking-wide text-ink-300">Rain now</dt>
                    <dd className="mt-1 font-medium">
                      {formatWithUnit(currentRecord.precipitation_mm, "mm", 1)}
                    </dd>
                  </div>
                  <div className="rounded-xl bg-black/15 p-3">
                    <dt className="text-[0.65rem] uppercase tracking-wide text-ink-300">Cloud</dt>
                    <dd className="mt-1 font-medium">{formatPercent(currentRecord.cloud_cover)}</dd>
                  </div>
                </dl>
                <p className="mt-4 text-[0.7rem] leading-5 text-ink-200">
                  Provider forecast/analysis for Kolkata, not an official station observation.
                  Updated {formatRelative(current.data?.retrieved_at)}.
                </p>
              </>
            ) : (
              <div className="mt-5">
                <p className="text-sm leading-6 text-ink-100">
                  No current weather record has been ingested. Run the weather ingestion command or
                  check the data-status page.
                </p>
              </div>
            )}
          </div>
        </div>
      </section>

      <div className="shell space-y-16 py-12 sm:py-16">
        <section aria-labelledby="layer-status-heading">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="eyebrow">Data availability</p>
              <h2 id="layer-status-heading" className="mt-1 font-display text-2xl text-ink-950">
                Every layer states its condition
              </h2>
            </div>
            <Link to="/methodology#data-status" className="link text-sm">
              Why some layers are unavailable
            </Link>
          </div>
          {status.isLoading ? (
            <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <div key={index} className="h-24 animate-pulse rounded-2xl bg-white" />
              ))}
            </div>
          ) : status.isError ? (
            <ErrorState className="mt-5" error={status.error} onRetry={() => void status.refetch()} />
          ) : (
            <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {moduleEntries.map(([key, module]) => (
                <Link
                  key={key}
                  to={MODULE_LINKS[key] ?? "/methodology"}
                  className="group rounded-2xl border border-ink-100 bg-white p-4 shadow-panel transition hover:-translate-y-0.5 hover:border-ink-200"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-semibold text-ink-900">{MODULE_LABELS[key] ?? titleCase(key)}</p>
                    <StateBadge state={module.state} />
                  </div>
                  <p className="mt-2 line-clamp-2 text-xs leading-5 text-ink-500">
                    {module.reason ?? module.source?.name ?? "Source registered"}
                  </p>
                  <p className="mt-2 text-[0.68rem] text-ink-400">
                    {module.last_success_at
                      ? `Last success ${formatRelative(module.last_success_at)}`
                      : "No successful ingestion recorded"}
                  </p>
                </Link>
              ))}
            </div>
          )}
        </section>

        <section aria-labelledby="briefing-heading">
          <SectionHeading
            eyebrow="Decision support"
            title="Today's briefing"
            description="Rules run over stored records. Each statement links back to the evidence that produced it; missing inputs do not produce a guess."
            action={
              <Link to="/insights" className="btn-secondary text-sm">
                All insights
              </Link>
            }
          />
          {insights.isLoading ? (
            <div className="mt-6"><LoadingPanel label="Building the evidence-backed briefing" /></div>
          ) : insights.isError ? (
            <ErrorState className="mt-6" error={insights.error} onRetry={() => void insights.refetch()} />
          ) : visibleInsights.length ? (
            <div className="mt-6 grid gap-4 lg:grid-cols-3">
              {visibleInsights.map((insight) => (
                <InsightCard key={insight.rule_id} insight={insight} compact />
              ))}
            </div>
          ) : (
            <div className="panel-muted mt-6 p-6">
              <p className="font-display text-xl text-ink-900">No substantive alert-level insight right now</p>
              <p className="prose-civic mt-2 max-w-2xl">
                No rule crossed its deterministic threshold for the currently available data. This is
                not a statement that conditions are safe — it only means the stored evidence did not
                meet a rule threshold.
              </p>
              {insights.data?.insights.length ? (
                <Link to="/insights" className="btn-secondary mt-4 text-sm">
                  See data-availability notes
                </Link>
              ) : null}
            </div>
          )}
        </section>

        <section aria-labelledby="modules-heading">
          <SectionHeading
            eyebrow="City layers"
            title="What the city is reporting"
            description="Different observation systems, kept visibly separate. Each module is a doorway into its own provenance and limitations."
          />
          <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <Link to="/heat" className="panel group flex flex-col p-5 transition hover:-translate-y-0.5 hover:border-ink-200">
              <div className="flex items-start justify-between gap-2">
                <p className="eyebrow">Heat &amp; environment</p>
                <StateBadge state={heat.data?.state ?? "UNAVAILABLE"} />
              </div>
              <p className="mt-3 font-display text-2xl text-ink-950">
                {heat.data?.count ? `${heat.data.count} hot cells` : "No satellite scene"}
              </p>
              <p className="mt-2 text-xs leading-5 text-ink-500">
                {heat.data?.date
                  ? `Latest LST observations for ${formatDateTime(heat.data.date)}. Land-surface temperature, not air temperature.`
                  : heat.data?.reason ?? "Landsat/GEE credentials are not configured, so no observations exist."}
              </p>
              <span className="mt-4 text-xs font-semibold text-ink-700 group-hover:underline">Open heat layer →</span>
            </Link>

            <Link to="/rainfall" className="panel group flex flex-col p-5 transition hover:-translate-y-0.5 hover:border-ink-200">
              <div className="flex items-start justify-between gap-2">
                <p className="eyebrow">Rainfall</p>
                <StateBadge state={rainfall.data?.state ?? "UNAVAILABLE"} />
              </div>
              <p className="mt-3 font-display text-2xl text-ink-950">
                {rainfall.data ? `${formatNumber(rainfall.data.summary.next_24h_total_mm, 1)} mm` : "No forecast"}
              </p>
              <p className="mt-2 text-xs leading-5 text-ink-500">
                {rainfall.data
                  ? `Expected in the next 24 hours; peak probability ${formatPercent(rainfall.data.summary.next_24h_max_probability_pct)}.`
                  : rainfall.error
                    ? "Rainfall endpoint unavailable."
                    : "No rainfall forecast has been ingested."}
              </p>
              <span className="mt-4 text-xs font-semibold text-ink-700 group-hover:underline">Open rainfall →</span>
            </Link>

            <Link to="/air-quality" className="panel group flex flex-col p-5 transition hover:-translate-y-0.5 hover:border-ink-200">
              <div className="flex items-start justify-between gap-2">
                <p className="eyebrow">Air quality</p>
                <StateBadge state={air.data?.state ?? "UNAVAILABLE"} />
              </div>
              <p className="mt-3 font-display text-2xl text-ink-950">
                {air.data?.results[0]?.latest_measurement?.aqi
                  ? `AQI ${air.data.results[0].latest_measurement.aqi}`
                  : "No station data"}
              </p>
              <p className="mt-2 text-xs leading-5 text-ink-500">
                {air.data?.results[0]?.name
                  ? `${air.data.results[0].name} — one station, not a city-wide surface.`
                  : air.data?.reason ?? "CPCB_API_KEY is not configured; no station measurements exist."}
              </p>
              <span className="mt-4 text-xs font-semibold text-ink-700 group-hover:underline">Open air quality →</span>
            </Link>

            <Link to="/climate" className="panel group flex flex-col p-5 transition hover:-translate-y-0.5 hover:border-ink-200">
              <div className="flex items-start justify-between gap-2">
                <p className="eyebrow">Climate trends</p>
                <StateBadge state={climate.data?.state ?? "UNAVAILABLE"} />
              </div>
              <p className="mt-3 font-display text-2xl text-ink-950">
                {climate.data?.trends.annual_temperature
                  ? `${formatNumber(climate.data.trends.annual_temperature.slope_per_decade, 2)}°C/decade`
                  : "No long-term series"}
              </p>
              <p className="mt-2 text-xs leading-5 text-ink-500">
                {climate.data?.trends.annual_temperature
                  ? `${climate.data.trends.annual_temperature.start_year}–${climate.data.trends.annual_temperature.end_year} OLS slope. Descriptive, not attribution.`
                  : climate.data?.reason ?? "No ERA5-Land climate metrics have been ingested."}
              </p>
              <span className="mt-4 text-xs font-semibold text-ink-700 group-hover:underline">Open climate →</span>
            </Link>

            <Link to="/alerts" className="panel group flex flex-col p-5 transition hover:-translate-y-0.5 hover:border-ink-200">
              <div className="flex items-start justify-between gap-2">
                <p className="eyebrow">Official alerts</p>
                <StateBadge state={alerts.data?.state ?? "UNAVAILABLE"} />
              </div>
              <p className="mt-3 font-display text-2xl text-ink-950">
                {alerts.data?.count ? `${alerts.data.count} active` : "None available"}
              </p>
              <p className="mt-2 text-xs leading-5 text-ink-500">
                {alerts.data?.reason ?? alerts.data?.note ?? "Official IMD feed unavailable."}
              </p>
              <span className="mt-4 text-xs font-semibold text-ink-700 group-hover:underline">Open official alerts →</span>
            </Link>

            <Link to="/reports" className="panel group flex flex-col p-5 transition hover:-translate-y-0.5 hover:border-ink-200">
              <div className="flex items-start justify-between gap-2">
                <p className="eyebrow">Community reports</p>
                <StateBadge state={status.data?.modules.community?.state ?? "UNAVAILABLE"} />
              </div>
              <p className="mt-3 font-display text-2xl text-ink-950">
                {summary.data ? `${summary.data.total} this week` : "No reports"}
              </p>
              <p className="mt-2 text-xs leading-5 text-ink-500">
                {summary.data
                  ? `${summary.data.unverified} awaiting verification · ${summary.data.verified} verified/resolved. Resident observations, not official alerts.`
                  : "No public community reports in the last 7 days."}
              </p>
              <span className="mt-4 text-xs font-semibold text-ink-700 group-hover:underline">Open community reports →</span>
            </Link>
          </div>
        </section>

        <section className="grid gap-8 lg:grid-cols-[1.05fr_0.95fr]">
          <div>
            <SectionHeading eyebrow="Evidence, not assertion" title="How a claim earns its place" />
            <div className="mt-5 grid gap-3">
              {[
                {
                  title: "1 · Source first",
                  body: "Every record carries its provider, dataset, licence and whether it is official. A provider forecast is never labelled an official warning.",
                },
                {
                  title: "2 · Time and units stay attached",
                  body: "Observation time, retrieval time, expected refresh window and measurement units are shown with each number.",
                },
                {
                  title: "3 · Gaps stay visible",
                  body: "No stations, no scenes or no credentials produce an explicit unavailable state — not a synthetic value or a silent zero.",
                },
                {
                  title: "4 · Community is its own layer",
                  body: "Resident reports are marked unverified until a moderator checks them. They never auto-merge and never masquerade as official alerts.",
                },
              ].map((item) => (
                <div key={item.title} className="rounded-xl border border-ink-100 bg-white p-4">
                  <p className="text-sm font-semibold text-ink-900">{item.title}</p>
                  <p className="mt-1 text-xs leading-5 text-ink-600">{item.body}</p>
                </div>
              ))}
            </div>
          </div>

          <div>
            <SectionHeading
              eyebrow="Resident signal"
              title="Recent community reports"
              action={<Link to="/reports" className="link text-sm">All reports</Link>}
            />
            <div className="mt-5 space-y-3">
              {incidents.isLoading ? (
                <LoadingPanel label="Loading community reports" rows={2} />
              ) : incidents.isError ? (
                <ErrorState error={incidents.error} onRetry={() => void incidents.refetch()} />
              ) : incidents.data?.results.length ? (
                incidents.data.results.slice(0, 4).map((incident) => (
                  <Link
                    key={incident.id}
                    to={`/reports/${incident.id}`}
                    className="block rounded-xl border border-ink-100 bg-white p-4 transition hover:border-ink-200"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-ink-900">{incident.category_label}</span>
                      <span
                        className={
                          incident.verification_state === "VERIFIED"
                            ? "chip border-emerald-200 bg-emerald-50 text-emerald-800"
                            : "chip border-amber-200 bg-amber-50 text-amber-800"
                        }
                      >
                        {incident.verification_state === "VERIFIED" ? "Verified" : "Unverified"}
                      </span>
                      <span className="text-xs text-ink-400">{formatRelative(incident.occurred_at)}</span>
                    </div>
                    <p className="mt-1.5 text-xs leading-5 text-ink-600">{truncate(incident.description, 150)}</p>
                    <p className="mt-1.5 text-[0.68rem] text-ink-400">
                      {incident.neighbourhood?.name ?? incident.area.name}
                      {incident.address_text ? ` · ${incident.address_text}` : ""}
                    </p>
                  </Link>
                ))
              ) : (
                <div className="panel-muted p-5">
                  <p className="text-sm font-medium text-ink-800">No public reports in the last 7 days</p>
                  <p className="mt-1 text-xs leading-5 text-ink-500">
                    Community reports appear after authentication and moderation visibility rules.
                    Submitting one does not make it an official alert.
                  </p>
                  <Link to="/reports/new" className="btn-secondary mt-3 text-xs">Submit a report</Link>
                </div>
              )}
            </div>
          </div>
        </section>

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Analytical grid"
            value="1 km"
            detail="EPSG:32645 cells used to aggregate satellite and climate values. The grid is an analysis unit, not a measurement resolution."
          />
          <StatCard
            label="City boundary"
            value="OSM"
            detail="Community-maintained OpenStreetMap relation, not an official KMC boundary. Area and attribution are shown on the methodology page."
          />
          <StatCard
            label="Official warnings"
            value={alerts.data?.count ? String(alerts.data.count) : "—"}
            detail="Only source-issued warnings appear here. An empty feed is not evidence that conditions are safe."
            tone="warm"
          />
          <StatCard
            label="Data status updated"
            value={status.data ? formatRelative(status.data.generated_at) : "—"}
            detail={status.data ? `Generated ${formatDateTime(status.data.generated_at)} IST` : "Status endpoint unavailable"}
            tone="cool"
          />
        </section>

        {current.data && current.data.state !== "AVAILABLE" ? (
          <DataStateNotice
            state={current.data.state}
            title="Current weather may not reflect conditions now"
            reason={current.data.note}
          />
        ) : null}
      </div>
    </div>
  );
}
