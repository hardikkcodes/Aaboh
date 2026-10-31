import { Link } from "react-router-dom";

import { useDataStatus, useInsights } from "../api/queries";
import { DataStateNotice, StateBadge } from "../components/ui/DataState";
import { ErrorState, LoadingPanel } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";
import { SectionHeading } from "../components/ui/SectionHeading";
import { MODULE_LABELS, MODULE_LINKS, THRESHOLD_META } from "../lib/constants";
import { formatDateTime, formatNumber, formatRelative, titleCase } from "../lib/format";

function thresholdMeta(key: string) {
  return THRESHOLD_META[key] ?? { label: titleCase(key), unit: "", digits: 0 };
}

const EVIDENCE_TYPES = [
  {
    title: "Observation",
    body: "A measurement or retrieval at a known time and place, such as a CPCB station reading or a Landsat surface-temperature retrieval. Observations carry their native resolution; they are not silently turned into a neighbourhood measurement.",
  },
  {
    title: "Forecast",
    body: "Model output about future conditions, such as an Open-Meteo temperature or rainfall forecast. A forecast is not an official warning and can be wrong.",
  },
  {
    title: "Prediction",
    body: "An estimate produced by the project's ML artifact, for example predicted land-surface temperature. Predictions appear only when an evaluated model and real prediction run exist, with metrics and limitations attached.",
  },
  {
    title: "Official warning",
    body: "A warning issued by an authoritative source, currently the India Meteorological Department. Only source-issued warnings are labelled official. The feed is unavailable without configured credentials.",
  },
  {
    title: "Community report",
    body: "A resident observation submitted through this platform. It is labelled unverified until a moderator changes its status, is never auto-merged, and is never presented as an official alert.",
  },
  {
    title: "Derived insight",
    body: "A deterministic rule output over stored evidence. It names the evidence and caveats that produced it. It is decision support, not a warning service or medical advice.",
  },
];

const LIMITATIONS = [
  "The Kolkata boundary is a community-maintained OpenStreetMap relation (9381363), not an official KMC boundary or ward map. Area figures are computed from that geometry.",
  "Neighbourhoods are named OSM locality points, not official wards. Selecting a locality does not create a statistical area.",
  "Official IMD alerts are unavailable until IMD_API_KEY and the correct key header are confirmed with IMD.",
  "CPCB station air quality is unavailable until CPCB_API_KEY is configured and the data.gov.in resource can be reached. No station values are synthesised.",
  "The Landsat/GEE pipeline is implemented but no credential-backed export has run. Satellite layers, hotspots and heat predictions therefore remain unavailable in this environment.",
  "ERA5-Land is a reanalysis at roughly 9 km resolution, accessed through Open-Meteo. Climate trends are descriptive OLS slopes, not attribution or local exposure estimates.",
  "The heat ML pipeline has no real labelled dataset or evaluated artifact in this environment. No metrics are displayed without a reproducible evaluation run.",
  "Community reports can be mistaken, duplicated or stale. Moderation improves but does not guarantee accuracy. An empty map is not evidence of safety.",
];

export function MethodologyPage() {
  const status = useDataStatus();
  const insights = useInsights();
  const data = status.data;
  const moduleEntries = data ? Object.entries(data.modules) : [];

  return (
    <div className="shell space-y-14 py-10 sm:py-14">
      <PageHeader
        eyebrow="Methodology · limits · provenance"
        title="How this platform knows what it knows"
        description="Every number has a source, a time, a unit and a quality state. This page explains the evidence ladder, spatial framing, algorithms and the gaps that remain. Nothing here is filled in with synthetic data."
        aside={data ? <StateBadge state={Object.values(data.modules).some((module) => module.state === "AVAILABLE") ? "PARTIAL" : "UNAVAILABLE"} /> : null}
      />

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="panel p-5 sm:p-6">
          <p className="eyebrow">What it is</p>
          <p className="prose-civic mt-3">
            A civic climate-intelligence prototype for Kolkata that brings weather, official warnings,
            satellite heat, rainfall, air quality, climate context and resident reports into one
            inspectable interface. Each layer keeps its own provenance and failure states.
          </p>
        </div>
        <div className="panel p-5 sm:p-6">
          <p className="eyebrow">What it is not</p>
          <p className="prose-civic mt-3">
            Not an official warning service, emergency service, medical advice, flood-depth model,
            hyperlocal sensor network or causal climate-attribution study. Follow instructions from IMD,
            KMC and emergency services. Call 112 in an emergency.
          </p>
        </div>
      </section>

      <section id="data-status">
        <SectionHeading
          eyebrow="Live status"
          title="What is reporting right now"
          description="This is the same availability state used across the platform. A layer is never marked available merely because its page exists."
          action={
            <button type="button" className="btn-secondary text-xs" onClick={() => void status.refetch()}>
              Refresh status
            </button>
          }
        />
        {status.isError ? (
          <ErrorState className="mt-5" error={status.error} onRetry={() => void status.refetch()} />
        ) : status.isLoading ? (
          <div className="mt-5"><LoadingPanel label="Loading data availability" rows={4} /></div>
        ) : data ? (
          <>
            <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {moduleEntries.map(([key, module]) => (
                <div key={key} className="rounded-2xl border border-ink-100 bg-white p-4 shadow-panel">
                  <div className="flex items-start justify-between gap-2">
                    <Link to={MODULE_LINKS[key] ?? "/"} className="text-sm font-semibold text-ink-900 hover:underline">
                      {MODULE_LABELS[key] ?? titleCase(key)}
                    </Link>
                    <StateBadge state={module.state} />
                  </div>
                  <p className="mt-2 text-xs leading-5 text-ink-500">
                    {module.reason ?? module.source?.name ?? "Source registered."}
                  </p>
                  <p className="mt-2 text-[0.68rem] text-ink-400">
                    {module.last_success_at
                      ? `Last success ${formatRelative(module.last_success_at)}`
                      : "No successful ingestion recorded"}
                  </p>
                </div>
              ))}
            </div>
            <p className="mt-3 text-xs text-ink-400">
              Generated {formatDateTime(data.generated_at)} IST. Availability is derived from the last
              successful ingestion and each source&apos;s expected refresh window.
            </p>
          </>
        ) : null}
      </section>

      <section>
        <SectionHeading
          eyebrow="Evidence ladder"
          title="Six kinds of statement, kept separate"
          description="The distinction is structural, not cosmetic. A forecast cannot become an official warning by appearing on the same page, and a community report cannot become verified without a recorded moderation transition."
        />
        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {EVIDENCE_TYPES.map((item, index) => (
            <article key={item.title} className="panel p-5">
              <p className="text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-ink-400">
                {String(index + 1).padStart(2, "0")}
              </p>
              <h3 className="mt-1 font-display text-xl text-ink-950">{item.title}</h3>
              <p className="prose-civic mt-2">{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="panel p-5 sm:p-6">
          <p className="eyebrow">Geography</p>
          <h2 className="section-title mt-1">One city, one analytical grid</h2>
          <ul className="mt-4 space-y-3 text-sm leading-6 text-ink-600">
            <li>
              <strong className="text-ink-900">Boundary.</strong> OpenStreetMap relation 9381363
              (admin_level 8, Wikidata Q1348), measured at 200.00 km² during bootstrap. Community
              maintained, ODbL licensed, and explicitly not an official KMC boundary.
            </li>
            <li>
              <strong className="text-ink-900">Analytical grid.</strong> {data ? "Deterministic" : "A deterministic"} 1 km grid in
              EPSG:32645 (UTM zone 45N). Cell counts depend on boundary coverage. The grid is an
              aggregation unit, not a measurement resolution.
            </li>
            <li>
              <strong className="text-ink-900">External geometry.</strong> GeoJSON is exchanged in
              EPSG:4326 (WGS 84). Projection happens server-side; the browser receives lon/lat
              coordinates.
            </li>
            <li>
              <strong className="text-ink-900">Localities.</strong> 124 OSM named locality points are
              searchable. They are points of reference, not wards, polygons or statistical zones.
            </li>
            <li>
              <strong className="text-ink-900">Aggregation.</strong> Native satellite and reanalysis
              values are aggregated to cells with a coverage fraction. A cell value is never described
              as a point observation.
            </li>
          </ul>
        </div>

        <div className="space-y-4">
          <div className="panel p-5 sm:p-6">
            <p className="eyebrow">Weather &amp; rainfall</p>
            <h2 className="section-title mt-1">Forecast, not station truth</h2>
            <p className="prose-civic mt-3">
              Open-Meteo supplies hourly forecasts, current conditions and a historical archive. Values
              are model output selected for the requested point; native grid spacing varies by model and
              variable. Rainfall summaries are sums over the returned hourly series, not gauge
              measurements. The platform does not claim a station observation it does not have.
            </p>
          </div>
          <div className="panel p-5 sm:p-6">
            <p className="eyebrow">Climate</p>
            <h2 className="section-title mt-1">Reanalysis context</h2>
            <p className="prose-civic mt-3">
              ERA5-Land daily aggregates are accessed via the Open-Meteo archive at roughly 9 km native
              resolution. Annual and seasonal series use complete calendar years. Trends are ordinary
              least-squares slopes over annual values, with the number of years reported. Short records
              and autocorrelation limit interpretation. Nothing here is causal attribution.
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="panel p-5 sm:p-6">
          <p className="eyebrow">Heat &amp; satellite</p>
          <h2 className="section-title mt-1">Land surface is not air temperature</h2>
          <p className="prose-civic mt-3">
            Landsat Collection 2 Level 2 imagery is processed through Google Earth Engine for
            land-surface temperature, NDVI, NDBI and MNDWI. Reflective bands are 30 m; the thermal
            product is delivered at 100 m. Values are aggregated to 1 km analytical cells, filtered for
            cloud cover and valid-pixel fraction. LST responds to surface materials and sun exposure; it
            is not the air temperature a person experiences and is not an official heat warning.
          </p>
          <p className="prose-civic mt-3">
            Hotspots are observed cells at or above the 90th percentile for the latest usable scene.
            They are descriptive, not a heat-health risk model.
          </p>
        </div>
        <div className="panel p-5 sm:p-6">
          <p className="eyebrow">Heat ML</p>
          <h2 className="section-title mt-1">An artifact, not a promise</h2>
          <p className="prose-civic mt-3">
            The ML package trains an XGBoost regressor on a chronological holdout. Training refuses
            datasets below 500 rows, 20 dates or 10 test dates. Metrics and a manifest are written beside
            the artifact; a Django registration command validates them before predictions can be
            ingested. Metrics are displayed only from a real evaluated artifact.
          </p>
          <p className="prose-civic mt-3">
            In this environment no credential-backed Landsat dataset has been produced, so no model has
            been trained, registered or used for prediction. The interface states this rather than
            substituting a heuristic map.
          </p>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="panel p-5 sm:p-6">
          <p className="eyebrow">Air quality</p>
          <h2 className="section-title mt-1">Station values stay station values</h2>
          <p className="prose-civic mt-3">
            CPCB measurements are read from the data.gov.in resource when credentials are configured.
            Each station keeps its own coordinates and timestamp. Measurements are not interpolated into
            a city-wide surface, and a missing station is not replaced by a nearby one. AQI categories
            follow the published station value; the platform does not invent an AQI where the source
            does not provide one.
          </p>
        </div>
        <div className="panel p-5 sm:p-6">
          <p className="eyebrow">Official alerts</p>
          <h2 className="section-title mt-1">Only the source can issue a warning</h2>
          <p className="prose-civic mt-3">
            The IMD adapter normalises source-issued warnings and preserves the external identifier,
            issue time, effective window, severity, area text and source URL. Without
            <code className="mx-1 rounded bg-ink-100 px-1 py-0.5 text-xs">IMD_API_KEY</code>
            the feed is unavailable. An empty alert list is not evidence that conditions are safe.
          </p>
        </div>
      </section>

      <section>
        <SectionHeading
          eyebrow="Community reports"
          title="Visible uncertainty, auditable moderation"
          description="Reports are data with a social process attached, not anonymous truth."
        />
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[
            { title: "Authentication", body: "Submission requires an account so a report can be attributed internally, edited safely and moderated. Email and identity are never public." },
            { title: "Image handling", body: "JPEG, PNG and WebP only, with size and dimension limits. EXIF metadata is stripped and images are re-encoded by the server." },
            { title: "Moderation", body: "Only moderators can change status. Every transition is recorded with a note and timestamp, without exposing moderator identity." },
            { title: "Duplicate hints", body: "Nearby reports of the same category within 250 m and 6 hours are suggested as possible duplicates. They are never merged automatically." },
            { title: "Edit policy", body: "Owners can edit while submitted or under review. Verified, resolved, rejected and duplicate reports are locked to preserve the audit trail." },
            { title: "Public visibility", body: "Rejected, duplicate and expired reports are hidden from public lists. Owners and moderators can still see them." },
          ].map((item) => (
            <div key={item.title} className="rounded-xl border border-ink-100 bg-white p-4">
              <p className="text-sm font-semibold text-ink-900">{item.title}</p>
              <p className="mt-1 text-xs leading-5 text-ink-600">{item.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <SectionHeading
          eyebrow="Rule engine"
          title="Deterministic thresholds over stored evidence"
          description={insights.data?.methodology ?? "The briefing evaluates deterministic rules over stored records and omits any rule whose required input is missing."}
          action={insights.data ? <StateBadge state={insights.data.state} /> : null}
        />
        {insights.data?.thresholds ? (
          <div className="panel mt-5 p-5 sm:p-6">
            <p className="eyebrow">Current ruleset {insights.data.ruleset_version}</p>
            <dl className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {Object.entries(insights.data.thresholds).map(([key, value]) => {
                const meta = thresholdMeta(key);
                return (
                  <div key={key} className="rounded-xl border border-ink-100 bg-ink-50 p-3">
                    <dt className="text-[0.65rem] uppercase tracking-wide text-ink-500">{meta.label}</dt>
                    <dd className="mt-1 text-sm font-semibold text-ink-900">
                      {formatNumber(value, meta.digits)} {meta.unit}
                    </dd>
                  </div>
                );
              })}
            </dl>
            <p className="mt-4 text-xs leading-5 text-ink-500">
              {insights.data.disclaimer} Threshold values are configuration, not calibrated safety
              limits, and must not be used as a substitute for official guidance.
            </p>
            <Link to="/insights" className="btn-secondary mt-4 text-xs">Open the briefing</Link>
          </div>
        ) : (
          <div className="panel-muted mt-5 p-5">
            <p className="text-sm font-medium text-ink-800">Threshold metadata is currently unavailable.</p>
            <p className="mt-1 text-xs leading-5 text-ink-500">
              The briefing endpoint could not be reached, so no threshold values are shown.
            </p>
          </div>
        )}
      </section>

      <section>
        <SectionHeading
          eyebrow="Known limitations"
          title="What remains blocked or uncertain"
          description="These are current conditions, not a backlog of intended features. When a blocker is removed, the relevant layer can move to an available state without changing the claim."
        />
        <ul className="mt-5 grid gap-3">
          {LIMITATIONS.map((item) => (
            <li key={item} className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50/60 p-4 text-sm leading-6 text-amber-950">
              <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-amber-500" aria-hidden="true" />
              {item}
            </li>
          ))}
        </ul>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div>
          <SectionHeading
            eyebrow="Sources"
            title="Registered providers and licences"
            description="Source records are seeded by migration and referenced by every stored observation. Attribution is part of the data model."
          />
          {data ? (
            <div className="mt-5 overflow-x-auto">
              <table className="table-civic min-w-[640px]">
                <thead>
                  <tr>
                    <th scope="col">Source</th>
                    <th scope="col">Type</th>
                    <th scope="col">Resolution</th>
                    <th scope="col">State</th>
                    <th scope="col">Last success</th>
                  </tr>
                </thead>
                <tbody>
                  {data.sources.map((source) => (
                    <tr key={source.slug}>
                      <td>
                        <span className="font-medium text-ink-900">{source.name}</span>
                        {source.is_official ? (
                          <span className="ml-2 chip border-emerald-200 bg-emerald-50 text-emerald-800">Official</span>
                        ) : null}
                        <span className="mt-1 block max-w-sm text-xs text-ink-500">{source.attribution}</span>
                      </td>
                      <td>{titleCase(source.provider_type)}</td>
                      <td>
                        {source.spatial_resolution_m
                          ? source.spatial_resolution_m >= 1000
                            ? `~${Math.round(source.spatial_resolution_m / 1000)} km`
                            : `${source.spatial_resolution_m} m`
                          : "Point / event"}
                      </td>
                      <td><StateBadge state={source.state} /></td>
                      <td>{source.last_success_at ? formatRelative(source.last_success_at) : "Never"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="prose-civic mt-4">Source metadata is unavailable.</p>
          )}
        </div>

        <div className="panel p-5 sm:p-6">
          <p className="eyebrow">Credentials</p>
          <h2 className="section-title mt-1">Provider configuration</h2>
          <p className="prose-civic mt-3">
            Presence of a credential does not prove a successful ingestion. The layer state and last
            success time remain the authority.
          </p>
          {data ? (
            <ul className="mt-4 space-y-2">
              {Object.entries(data.providers).map(([key, provider]) => (
                <li key={key} className="flex items-center justify-between gap-3 rounded-xl border border-ink-100 p-3 text-sm">
                  <span className="font-medium text-ink-900">{titleCase(key)}</span>
                  <span className={provider.configured ? "chip border-emerald-200 bg-emerald-50 text-emerald-800" : "chip border-ink-200 bg-ink-50 text-ink-700"}>
                    {provider.configured ? "Configured" : "Not configured"}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-xs text-ink-500">Provider configuration is unavailable.</p>
          )}
          <DataStateNotice
            className="mt-4"
            state="PARTIAL"
            title="Configuration is not observation"
            reason="A configured key can still fail, time out or return no records. Read each layer's state before relying on it."
          />
        </div>
      </section>

      <p className="text-xs leading-5 text-ink-500">
        This page describes the software as deployed in this environment. Where an integration requires
        credentials or an external asset, the page and API report the layer as unavailable rather than
        presenting simulated values. Source attribution and licences are attached to the underlying
        records and repeated in the interface.
      </p>
    </div>
  );
}
