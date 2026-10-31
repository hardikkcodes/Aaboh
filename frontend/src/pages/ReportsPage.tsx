import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useArea, useIncidents, useIncidentSummary } from "../api/queries";
import { useAuth } from "../auth/context";
import { IncidentMap } from "../components/map/IncidentMap";
import { DataStateNotice } from "../components/ui/DataState";
import { EmptyState, ErrorState, LoadingPanel } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";
import { SectionHeading } from "../components/ui/SectionHeading";
import { StatCard } from "../components/ui/StatCard";
import { INCIDENT_CATEGORIES, INCIDENT_STATUSES } from "../lib/constants";
import { formatDateTime, formatRelative, titleCase, truncate } from "../lib/format";

export function ReportsPage() {
  const [searchParams] = useSearchParams();
  const { isAuthenticated } = useAuth();
  const areaSlug = searchParams.get("area") ?? "kolkata";
  const searchName = searchParams.get("name");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [sinceHours, setSinceHours] = useState(0);
  const [mine, setMine] = useState(false);

  const area = useArea(areaSlug);
  const summary = useIncidentSummary(areaSlug);
  const incidents = useIncidents({
    area: areaSlug,
    category: category || undefined,
    status: status || undefined,
    since_hours: sinceHours || undefined,
    mine: mine && isAuthenticated,
  });

  const results = incidents.data?.results ?? [];

  return (
    <div className="shell space-y-6 py-5 sm:py-8">
      <PageHeader
        eyebrow="Community · resident observations"
        title="What residents are reporting"
        description="Authenticated residents can submit local environmental observations. Reports stay visibly unverified until a moderator checks them. They are not official alerts and are never auto-merged."
        aside={
          <Link to="/reports/new" className="btn-primary text-sm">
            Submit a report
          </Link>
        }
      />

      {searchName ? (
        <div className="rounded-xl border border-ink-200 bg-white p-3 text-sm text-ink-600">
          Showing reports for <span className="font-semibold text-ink-900">{searchName}</span> and the{" "}
          {area.data?.name ?? areaSlug} area. Use the map and report text to judge the exact location.
        </div>
      ) : null}

      <DataStateNotice
        state="PARTIAL"
        title="Community reports are observations, not warnings"
        reason="Anyone can be mistaken, duplicate a report or describe a location imprecisely. Moderator verification is shown explicitly; unverified reports remain labelled as such everywhere."
      />

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Reports this week"
          value={summary.data ? String(summary.data.total) : "—"}
          detail="Public reports in the last 7 days"
        />
        <StatCard
          label="Awaiting verification"
          value={summary.data ? String(summary.data.unverified) : "—"}
          detail="Submitted or under review"
          tone="warm"
        />
        <StatCard
          label="Verified / resolved"
          value={summary.data ? String(summary.data.verified) : "—"}
          detail="Checked by a moderator"
        />
        <StatCard
          label="Filtered result"
          value={incidents.data ? String(incidents.data.count) : "—"}
          detail="Reports matching the current filters"
          tone="cool"
        />
      </section>

      <section className="panel grid gap-4 p-4 sm:grid-cols-2 sm:p-5 lg:grid-cols-[1fr_1fr_1fr_auto]">
        <div>
          <label className="label" htmlFor="report-category">Category</label>
          <select
            id="report-category"
            className="field"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
          >
            <option value="">All categories</option>
            {INCIDENT_CATEGORIES.map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="report-status">Status</label>
          <select
            id="report-status"
            className="field"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="">All visible statuses</option>
            {INCIDENT_STATUSES.map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="report-window">Created within</label>
          <select
            id="report-window"
            className="field"
            value={sinceHours}
            onChange={(event) => setSinceHours(Number(event.target.value))}
          >
            <option value={0}>Any time</option>
            <option value={24}>Last 24 hours</option>
            <option value={24 * 7}>Last 7 days</option>
            <option value={24 * 30}>Last 30 days</option>
          </select>
        </div>
        <div className="flex items-end">
          <label className={`flex w-full items-center gap-2 rounded-xl border px-3 py-2.5 text-sm ${isAuthenticated ? "border-ink-200 bg-white text-ink-700" : "border-ink-100 bg-ink-50 text-ink-400"}`}>
            <input
              type="checkbox"
              checked={mine}
              disabled={!isAuthenticated}
              onChange={(event) => setMine(event.target.checked)}
              className="h-4 w-4 rounded border-ink-300"
            />
            Only my reports
          </label>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <div>
          <SectionHeading eyebrow="Map" title="Reported locations" />
          <div className="mt-4">
            {incidents.isLoading ? (
              <LoadingPanel label="Loading report locations" rows={2} />
            ) : incidents.isError ? (
              <ErrorState error={incidents.error} onRetry={() => void incidents.refetch()} />
            ) : (
              <IncidentMap incidents={results} boundary={area.data?.boundary} height="420px" />
            )}
          </div>
        </div>
        <div>
          <SectionHeading eyebrow="Interpretation" title="Reading the map" />
          <div className="panel mt-4 space-y-3 p-5 text-sm leading-6 text-ink-600">
            <p>
              Green points have been checked by a moderator. Amber points are unverified reports and
              may be inaccurate, duplicated or stale.
            </p>
            <p>
              A cluster can reflect a real local issue or several residents reporting the same event.
              The platform suggests duplicates but never merges reports automatically.
            </p>
            <p>
              No report at a location does not mean the location is unaffected. This map is not a
              flood, heat or safety assessment.
            </p>
          </div>
        </div>
      </section>

      <section>
        <SectionHeading
          eyebrow="Reports"
          title={results.length ? `${results.length} report${results.length === 1 ? "" : "s"}` : "Community reports"}
          action={<Link to="/reports/new" className="btn-secondary text-sm">Add your observation</Link>}
        />
        {incidents.isLoading ? (
          <div className="mt-5"><LoadingPanel label="Loading community reports" /></div>
        ) : incidents.isError ? (
          <ErrorState className="mt-5" error={incidents.error} onRetry={() => void incidents.refetch()} />
        ) : results.length ? (
          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {results.map((incident) => (
              <Link
                key={incident.id}
                to={`/reports/${incident.id}`}
                className="panel group flex h-full flex-col p-5 transition hover:-translate-y-0.5 hover:border-ink-200"
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
                  {incident.is_owner ? (
                    <span className="chip border-sky-200 bg-sky-50 text-sky-800">Yours</span>
                  ) : null}
                </div>
                <p className="mt-3 flex-1 text-sm leading-6 text-ink-600">{truncate(incident.description, 190)}</p>
                <dl className="mt-4 space-y-1 text-xs text-ink-500">
                  <div className="flex justify-between gap-2">
                    <dt>Status</dt>
                    <dd className="font-medium text-ink-700">{titleCase(incident.status)}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt>Occurred</dt>
                    <dd>{formatRelative(incident.occurred_at)}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt>Location</dt>
                    <dd className="text-right">{incident.neighbourhood?.name ?? `${incident.latitude.toFixed(4)}, ${incident.longitude.toFixed(4)}`}</dd>
                  </div>
                  {incident.attachments_count ? (
                    <div className="flex justify-between gap-2">
                      <dt>Images</dt>
                      <dd>{incident.attachments_count}</dd>
                    </div>
                  ) : null}
                </dl>
                <span className="mt-4 text-xs font-semibold text-ink-700 group-hover:underline">Open report →</span>
              </Link>
            ))}
          </div>
        ) : (
          <EmptyState
            className="mt-5"
            title="No reports match these filters"
            description="Try a wider time window or clear the category and status filters. If there are genuinely no reports, this space remains empty rather than being filled with examples."
            action={<Link to="/reports/new" className="btn-primary text-sm">Submit the first report</Link>}
          />
        )}
      </section>

      <p className="text-xs leading-5 text-ink-500">
        Reports older than the public listing window may still exist. Public visibility excludes rejected,
        duplicate and expired reports. Audit history is available on each report.{" "}
        {summary.data ? `Summary generated for ${summary.data.window_hours} hours.` : null}
      </p>
      <p className="text-xs text-ink-400">Report times are stored with provenance and shown in IST ({formatDateTime(new Date().toISOString())} now).</p>
    </div>
  );
}
