import { TriangleAlert } from "lucide-react";
import { useMemo, useState } from "react";

import { useAlerts } from "../api/queries";
import type { Alert } from "../api/types";
import { DataStateNotice, StateBadge } from "../components/ui/DataState";
import { ErrorState, EmptyState, LoadingPanel } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";
import { SourcePanel } from "../components/ui/SourcePanel";
import { formatDateTime, formatRelative, titleCase } from "../lib/format";

const severityStyles: Record<string, string> = {
  extreme: "border-red-300 bg-red-100 text-red-900",
  severe: "border-red-200 bg-red-50 text-red-800",
  moderate: "border-amber-200 bg-amber-50 text-amber-800",
  minor: "border-sky-200 bg-sky-50 text-sky-800",
  unknown: "border-ink-200 bg-ink-50 text-ink-700",
};

function AlertCard({ alert }: { alert: Alert }) {
  return (
    <article className="panel p-5 sm:p-6">
      <div className="flex flex-wrap items-center gap-2">
        {alert.match === "state" ? (
          <span className="chip border-amber-200 bg-amber-50 text-amber-800">State-level: check your district</span>
        ) : null}
        <span className={`chip ${severityStyles[alert.severity] ?? severityStyles.unknown}`}>
          {alert.severity_label || titleCase(alert.severity)}
        </span>
        <span className="chip border-ink-200 bg-white text-ink-700">{alert.hazard_label || titleCase(alert.hazard)}</span>
        {alert.is_current ? (
          <span className="chip border-emerald-200 bg-emerald-50 text-emerald-800">Currently active</span>
        ) : (
          <span className="chip border-ink-200 bg-ink-50 text-ink-600">Not current</span>
        )}
        <span className="ml-auto text-xs text-ink-400">Issued {formatRelative(alert.issued_at)}</span>
      </div>

      <h2 data-original-text className="mt-3 flex items-start gap-2 font-display text-2xl leading-snug text-ink-950"><TriangleAlert className="mt-1 h-5 w-5 shrink-0 text-amber-600" aria-hidden="true" />{alert.title}</h2>
      <p data-original-text className="prose-civic mt-2 whitespace-pre-line">{alert.description}</p>

      <dl className="mt-4 grid gap-x-6 gap-y-2 text-xs sm:grid-cols-2">
        <div>
          <dt className="font-semibold uppercase tracking-wide text-ink-500">Areas</dt>
          <dd className="mt-0.5 text-ink-700">{alert.areas_text || "Not stated in the source record"}</dd>
        </div>
        <div>
          <dt className="font-semibold uppercase tracking-wide text-ink-500">Issued</dt>
          <dd className="mt-0.5 text-ink-700">{formatDateTime(alert.issued_at)}</dd>
        </div>
        <div>
          <dt className="font-semibold uppercase tracking-wide text-ink-500">Effective</dt>
          <dd className="mt-0.5 text-ink-700">{formatDateTime(alert.effective_at)}</dd>
        </div>
        <div>
          <dt className="font-semibold uppercase tracking-wide text-ink-500">Expires</dt>
          <dd className="mt-0.5 text-ink-700">{formatDateTime(alert.expires_at)}</dd>
        </div>
        <div>
          <dt className="font-semibold uppercase tracking-wide text-ink-500">Certainty / urgency</dt>
          <dd className="mt-0.5 text-ink-700">
            {titleCase(alert.certainty)} · {titleCase(alert.urgency)}
          </dd>
        </div>
        <div>
          <dt className="font-semibold uppercase tracking-wide text-ink-500">Source record</dt>
          <dd className="mt-0.5 text-ink-700">{alert.source.name ?? "Official source"}</dd>
        </div>
      </dl>

      <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-ink-100 pt-3 text-xs">
        <a href={alert.source_url} target="_blank" rel="noreferrer" className="link">
          Read the original bulletin
        </a>
        <span className="text-ink-400">
          Retrieved {formatDateTime(alert.retrieved_at)} · External ID {alert.external_id}
        </span>
      </div>
    </article>
  );
}

export function AlertsPage() {
  const alerts = useAlerts();
  const [severity, setSeverity] = useState("all");
  const [hazard, setHazard] = useState("all");

  const hazards = useMemo(
    () => Array.from(new Set((alerts.data?.results ?? []).map((alert) => alert.hazard))).sort(),
    [alerts.data],
  );
  const filtered = (alerts.data?.results ?? []).filter((alert) => {
    if (severity !== "all" && alert.severity !== severity) return false;
    if (hazard !== "all" && alert.hazard !== hazard) return false;
    return true;
  });

  return (
    <div className="shell space-y-6 py-5 sm:py-8">
      <PageHeader
        eyebrow="Official warnings"
        title="Official warnings for your area"
        description="Warnings from IMD, CWC and state disaster agencies, published on the national SACHET service. We show them as issued. If this list is empty, stay alert: it doesn't mean conditions are safe."
        aside={alerts.data ? <StateBadge state={alerts.data.state} /> : null}
      />

      {alerts.isError ? (
        <ErrorState error={alerts.error} onRetry={() => void alerts.refetch()} />
      ) : alerts.isLoading ? (
        <LoadingPanel label="Loading the official alert feed" />
      ) : (
        <>
          <DataStateNotice
            state={alerts.data?.state ?? "UNAVAILABLE"}
            title={
              alerts.data?.state === "UNAVAILABLE"
                ? "Official alert feed is not available"
                : "Official alert coverage is limited"
            }
            reason={alerts.data?.reason ?? null}
          >
            <p>
              {alerts.data?.feed_message ??
                "The platform does not generate substitute warnings from forecasts or community reports."}
            </p>
          </DataStateNotice>

          {alerts.data?.count ? (
            <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-950">
              {alerts.data.feed_message ?? `${alerts.data.count} active official warning(s).`}
            </p>
          ) : alerts.data?.state === "AVAILABLE" ? (
            <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
              {alerts.data.feed_message ??
                "The official alert feed is reachable. No active warning covers this area right now."}
            </p>
          ) : null}

          {alerts.data?.results.length ? (
            <>
              <section className="panel flex flex-wrap items-end gap-4 p-4 sm:p-5" aria-label="Filter alerts">
                <div>
                  <label className="label" htmlFor="alert-severity">Severity</label>
                  <select
                    id="alert-severity"
                    className="field !w-auto min-w-40"
                    value={severity}
                    onChange={(event) => setSeverity(event.target.value)}
                  >
                    <option value="all">All severities</option>
                    {Array.from(new Set(alerts.data.results.map((alert) => alert.severity))).map((value) => (
                      <option key={value} value={value}>{titleCase(value)}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label" htmlFor="alert-hazard">Hazard</label>
                  <select
                    id="alert-hazard"
                    className="field !w-auto min-w-40"
                    value={hazard}
                    onChange={(event) => setHazard(event.target.value)}
                  >
                    <option value="all">All hazards</option>
                    {hazards.map((value) => (
                      <option key={value} value={value}>{titleCase(value)}</option>
                    ))}
                  </select>
                </div>
                <p className="ml-auto text-xs text-ink-500">
                  Showing {filtered.length} of {alerts.data.count}
                </p>
              </section>

              <div className="space-y-4">
                {filtered.length ? (
                  filtered.map((alert) => <AlertCard key={alert.id} alert={alert} />)
                ) : (
                  <EmptyState
                    title="No warnings match these filters"
                    description="Clear the filters to see all source-issued warnings. This does not mean there are no hazards."
                  />
                )}
              </div>
            </>
          ) : (
            <EmptyState
              title={
                alerts.data?.state === "AVAILABLE"
                  ? "No active official warning covers this area"
                  : "No official warnings are available to display"
              }
              description={
                alerts.data?.state === "AVAILABLE"
                  ? alerts.data.feed_message ??
                    "The SACHET feed was refreshed and returned no warning for this area. This does not mean conditions are safe; follow IMD and KMC during severe weather."
                  : "The official alert feed could not be read and no stored warning for this area is available. The platform will not fill this space with forecasts or community reports. Follow IMD and KMC directly during severe weather."
              }
              action={<a className="btn-secondary" href="https://sachet.ndma.gov.in/" target="_blank" rel="noreferrer">Visit SACHET</a>}
            />
          )}

          <section className="grid gap-4 md:grid-cols-3">
            {[
              {
                title: "Official",
                body: "Only records issued by the authority appear in this list. Provider forecasts and community reports are shown on separate pages with their own labels.",
              },
              {
                title: "Scope",
                body: "Warnings that name your area are listed first. Some only name the state, so they are marked to check your district in the bulletin.",
              },
              {
                title: "No warning ≠ safe",
                body: "Absence of an alert can reflect a gap in ingestion. The data-status page shows whether the SACHET feed is reachable and when it last succeeded.",
              },
            ].map((item) => (
              <div key={item.title} className="panel p-5">
                <p className="eyebrow">{item.title}</p>
                <p className="prose-civic mt-2">{item.body}</p>
              </div>
            ))}
          </section>
        </>
      )}

      <SourcePanel
        source={alerts.data?.source}
        lastSuccessAt={alerts.data?.last_success_at}
        note={alerts.data?.note}
        extra={
          <p className="text-xs leading-5 text-ink-500">
            Alert geometry is preserved when the provider supplies it; SACHET does not, so its alerts are scoped by the published area text. The platform never expands a warning's geographic scope and never rewrites its severity.
          </p>
        }
      />
    </div>
  );
}
