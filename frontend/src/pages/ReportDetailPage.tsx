import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { fieldErrors, normalizeError } from "../api/client";
import { useArea, useIncident, useModerateIncident } from "../api/queries";
import { useAuth } from "../auth/context";
import { ComplaintDraft } from "../components/live/ComplaintDraft";
import { ReportConfirmButtons } from "../components/live/ReportConfirmButtons";
import { IncidentMap } from "../components/map/IncidentMap";
import { StateBadge } from "../components/ui/DataState";
import { ErrorState, InlineSpinner, LoadingPanel } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";
import { SectionHeading } from "../components/ui/SectionHeading";
import { MODERATOR_STATUSES, TRUST_META } from "../lib/constants";
import { formatDateTime, formatNumber, formatRelative, titleCase } from "../lib/format";

const STATUS_TRANSITIONS: Record<string, string[]> = {
  SUBMITTED: ["UNDER_REVIEW", "VERIFIED", "REJECTED", "DUPLICATE", "EXPIRED"],
  UNDER_REVIEW: ["VERIFIED", "REJECTED", "DUPLICATE", "EXPIRED"],
  VERIFIED: ["RESOLVED", "EXPIRED"],
  RESOLVED: [],
  REJECTED: ["UNDER_REVIEW"],
  EXPIRED: ["UNDER_REVIEW"],
  DUPLICATE: ["UNDER_REVIEW"],
};

function statusClasses(status: string): string {
  if (status === "VERIFIED" || status === "RESOLVED") {
    return "chip border-emerald-200 bg-emerald-50 text-emerald-800";
  }
  if (["REJECTED", "DUPLICATE", "EXPIRED"].includes(status)) {
    return "chip border-ink-200 bg-ink-50 text-ink-700";
  }
  return "chip border-amber-200 bg-amber-50 text-amber-800";
}

function statusLabel(status: string): string {
  const found = MODERATOR_STATUSES.find((item) => item === status);
  return found ? titleCase(found) : titleCase(status);
}

export function ReportDetailPage() {
  const { id } = useParams();
  const { user, isModerator, isAuthenticated } = useAuth();
  const incident = useIncident(id);
  const area = useArea(incident.data?.area.slug ?? "kolkata");
  const moderate = useModerateIncident(id ?? "");
  const [nextStatus, setNextStatus] = useState("");
  const [note, setNote] = useState("");
  const [duplicateOf, setDuplicateOf] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);

  if (incident.isLoading) {
    return <div className="shell py-16"><LoadingPanel label="Loading community report" rows={4} /></div>;
  }
  if (incident.isError) {
    return (
      <div className="shell max-w-3xl py-16">
        <ErrorState error={incident.error} onRetry={() => void incident.refetch()} />
        <Link to="/reports" className="btn-secondary mt-4">Back to reports</Link>
      </div>
    );
  }
  if (!incident.data) {
    return (
      <div className="shell max-w-3xl py-16">
        <div className="panel p-8 text-center">
          <p className="eyebrow">Community report</p>
          <h1 className="display-title mt-2">Report not found or not public</h1>
          <p className="prose-civic mx-auto mt-3 max-w-xl">
            The report may have been rejected, marked duplicate, expired, or removed from public
            visibility. Reports remain visible to their owner and to moderators.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link to="/reports" className="btn-secondary">Back to reports</Link>
            {isAuthenticated ? <Link to="/account" className="btn-ghost">Your account</Link> : null}
          </div>
        </div>
      </div>
    );
  }

  const report = incident.data;
  const history = report.status_history ?? [];
  const hints = report.potential_duplicates ?? [];
  const canEdit = isModerator || (report.is_owner && ["SUBMITTED", "UNDER_REVIEW"].includes(report.status));
  const transitions = STATUS_TRANSITIONS[report.status] ?? [];
  const normalizedError = moderate.isError ? normalizeError(moderate.error) : null;
  const allowedDuplicateHints = hints.filter((hint) => hint.id !== report.id);

  async function handleModerate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    if (!nextStatus) {
      setFeedback("Choose the next moderation status.");
      return;
    }
    if (nextStatus === "DUPLICATE" && !duplicateOf.trim()) {
      setFeedback("A duplicate must reference the original report ID.");
      return;
    }
    try {
      const payload: Record<string, unknown> = { status: nextStatus, note: note.trim() };
      if (nextStatus === "DUPLICATE") payload.duplicate_of = duplicateOf.trim();
      const updated = await moderate.mutateAsync(payload);
      setFeedback(`Report moved to ${updated.status_label}.`);
      setNextStatus("");
      setNote("");
      setDuplicateOf("");
    } catch {
      // The normalized API error is rendered below.
    }
  }

  return (
    <div className="shell space-y-6 py-5 sm:py-8">
      <PageHeader
        eyebrow={`Community · ${report.area.name} · ${report.category_label}`}
        title={report.address_text || report.neighbourhood?.name || "Community report"}
        description="A resident observation. It is not an official alert, a forecast or a verified measurement. Read the verification state, timeline and location caveats before relying on it."
        aside={
          <div className="flex flex-wrap items-center gap-2">
            <span className={statusClasses(report.status)}>{report.status_label}</span>
            <span
              className={
                report.verification_state === "VERIFIED"
                  ? "chip border-emerald-200 bg-emerald-50 text-emerald-800"
                  : "chip border-amber-200 bg-amber-50 text-amber-800"
              }
            >
              {report.verification_state === "VERIFIED" ? "Verified by moderator" : "Unverified"}
            </span>
            {!report.is_public ? (
              <span className="chip border-ink-200 bg-ink-50 text-ink-700">Not public</span>
            ) : null}
          </div>
        }
      />

      {canEdit ? (
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-ink-100 bg-white p-3 text-sm">
          <span className="text-ink-600">You can edit this report while it remains editable.</span>
          <Link to={`/reports/${report.id}/edit`} className="btn-secondary text-xs">Edit report</Link>
          <Link to="/account" className="btn-ghost text-xs">Your reports</Link>
        </div>
      ) : null}

      <div className="grid gap-8 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="space-y-6">
          <article className="panel p-5 sm:p-6">
            <div className="flex flex-wrap items-center gap-2">
              <span className="chip border-ink-200 bg-white text-ink-600">{report.category_label}</span>
              <span className="chip border-ink-200 bg-white text-ink-600">
                {report.verification_state === "VERIFIED" ? "Moderator checked" : "Awaiting moderator check"}
              </span>
              {report.is_owner ? <span className="chip border-sky-200 bg-sky-50 text-sky-800">Yours</span> : null}
            </div>
            {report.description ? (
              <p className="mt-4 whitespace-pre-line text-sm leading-7 text-ink-700">{report.description}</p>
            ) : null}
            <div className="mt-4 rounded-xl border border-ink-100 bg-ink-50 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`chip ${TRUST_META[report.trust].classes}`}>{TRUST_META[report.trust].label}</span>
                {report.water_depth_label ? (
                  <span className="chip border-ink-200 bg-white text-ink-700">{report.water_depth_label}</span>
                ) : null}
                {report.passability_label ? (
                  <span className="chip border-ink-200 bg-white text-ink-700">{report.passability_label}</span>
                ) : null}
              </div>
              <p className="mt-2 text-xs text-ink-600">
                {report.is_active
                  ? `On the live map until ${formatDateTime(report.expires_at)}.`
                  : report.cleared_at
                    ? `Marked cleared ${formatRelative(report.cleared_at)}.`
                    : "No longer on the live map."}{" "}
                {report.confirmations.still_there} still there · {report.confirmations.cleared} cleared
                {isModerator ? ` · ${report.confirmations.wrong} looks wrong` : ""}
              </p>
              {report.is_active ? (
                <div className="mt-3">
                  <ReportConfirmButtons reportId={report.id} isOwner={report.is_owner} />
                </div>
              ) : null}
            </div>
            <dl className="mt-5 grid gap-3 border-t border-ink-100 pt-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">Occurred</dt>
                <dd className="mt-1 text-ink-800">{formatDateTime(report.occurred_at)}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">Submitted</dt>
                <dd className="mt-1 text-ink-800">{formatDateTime(report.created_at)}</dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">Area</dt>
                <dd className="mt-1 text-ink-800">
                  {report.area.name}
                  {report.neighbourhood ? ` · ${report.neighbourhood.name}` : ""}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">Last updated</dt>
                <dd className="mt-1 text-ink-800">{formatRelative(report.updated_at)}</dd>
              </div>
              {report.address_text ? (
                <div className="sm:col-span-2">
                  <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">Landmark</dt>
                  <dd className="mt-1 text-ink-800">{report.address_text}</dd>
                </div>
              ) : null}
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">Coordinates</dt>
                <dd className="mt-1 font-mono text-xs text-ink-700">
                  {formatNumber(report.latitude, 5)}, {formatNumber(report.longitude, 5)}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">Source</dt>
                <dd className="mt-1 text-ink-800">{report.source.name ?? "Community contributors"}</dd>
              </div>
            </dl>
            {report.verified_at || report.resolved_at ? (
              <p className="mt-4 text-xs text-ink-500">
                {report.verified_at ? `Verified ${formatDateTime(report.verified_at)}. ` : null}
                {report.resolved_at ? `Resolved ${formatDateTime(report.resolved_at)}. ` : null}
                Verification records a moderation decision; it does not make this an official warning.
              </p>
            ) : null}
            {report.moderation_note ? (
              <div className="mt-4 rounded-xl border border-ink-100 bg-ink-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Latest moderation note</p>
                <p className="mt-1 text-sm leading-6 text-ink-700">{report.moderation_note}</p>
              </div>
            ) : null}
          </article>

          <ComplaintDraft report={report} />

          {report.attachments?.length ? (
            <section>
              <SectionHeading eyebrow="Evidence" title={`Attached images (${report.attachments.length})`} />
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {report.attachments.map((attachment) => (
                  <figure key={attachment.id} className="panel overflow-hidden">
                    <a href={attachment.url} target="_blank" rel="noreferrer" className="block bg-ink-50">
                      <img
                        src={attachment.url}
                        alt={`Attachment to community report ${report.category_label}`}
                        className="h-52 w-full object-cover"
                        loading="lazy"
                      />
                    </a>
                    <figcaption className="px-3 py-2 text-[0.68rem] text-ink-500">
                      Uploaded {formatDateTime(attachment.created_at)} · {Math.round(attachment.size_bytes / 1024)} KB ·
                      metadata stripped
                    </figcaption>
                  </figure>
                ))}
              </div>
            </section>
          ) : (
            <div className="panel-muted p-5">
              <p className="text-sm font-medium text-ink-800">No images attached</p>
              <p className="mt-1 text-xs leading-5 text-ink-500">
                Images are optional. Their absence does not invalidate a report, and an image does not
                automatically verify one.
              </p>
            </div>
          )}

          <section>
            <SectionHeading
              eyebrow="Audit history"
              title="Moderation timeline"
              description="Every status change is recorded. Moderator identities are not exposed."
            />
            {history.length ? (
              <ol className="mt-4 space-y-3">
                {history.map((entry) => (
                  <li key={entry.id} className="panel flex gap-3 p-4">
                    <span className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full bg-ink-300" aria-hidden="true" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-ink-900">
                        {entry.from_status_label ? `${entry.from_status_label} → ` : ""}
                        {entry.to_status_label}
                      </p>
                      <p className="mt-0.5 text-xs text-ink-500">{formatDateTime(entry.created_at)}</p>
                      {entry.note ? <p className="mt-1 text-xs leading-5 text-ink-600">{entry.note}</p> : null}
                    </div>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="prose-civic mt-4">No moderation history is visible for this report.</p>
            )}
          </section>
        </div>

        <aside className="space-y-6">
          <section>
            <SectionHeading eyebrow="Location" title="Where it was reported" />
            <div className="mt-4">
              <IncidentMap incidents={[report]} boundary={area.data?.boundary} height="300px" />
            </div>
            <p className="mt-2 text-xs leading-5 text-ink-500">
              Coordinates are part of the public record. A report at a point does not describe the
              conditions of the whole neighbourhood, and no report at a point does not mean no impact.
            </p>
          </section>

          <div className="panel p-5">
            <p className="eyebrow">Reliance</p>
            <p className="prose-civic mt-2">
              {report.verification_state === "VERIFIED"
                ? "A moderator has checked this report. That is a moderation decision, not an official warning, measurement or safety certification."
                : "This report has not been checked by a moderator. It may be inaccurate, duplicated or stale. Treat it as one resident's observation."}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Link to="/reports" className="btn-secondary text-xs">All reports</Link>
              <Link to="/methodology" className="btn-ghost text-xs">How moderation works</Link>
            </div>
          </div>

          {hints.length ? (
            <div className="panel p-5">
              <p className="eyebrow">Possible duplicates</p>
              <p className="mt-2 text-xs leading-5 text-ink-500">
                Nearby reports of the same category within 250 m and 6 hours. These are hints only and
                have not been merged.
              </p>
              <ul className="mt-3 space-y-2">
                {hints.map((hint) => (
                  <li key={hint.id}>
                    <Link
                      to={`/reports/${hint.id}`}
                      className="block rounded-xl border border-ink-100 p-3 text-sm transition hover:border-ink-200"
                    >
                      <span className="font-medium text-ink-900">{titleCase(hint.category)}</span>
                      <span className="ml-2 chip border-ink-200 bg-white text-ink-600">
                        {hint.verification_state === "VERIFIED" ? "Verified" : "Unverified"}
                      </span>
                      <span className="mt-1 block text-xs text-ink-500">
                        {formatNumber(hint.distance_m, 0)} m away · {formatDateTime(hint.occurred_at)}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {isModerator ? (
            <form className="panel space-y-4 p-5" onSubmit={(event) => void handleModerate(event)}>
              <div>
                <p className="eyebrow">Moderator tools</p>
                <p className="mt-1 text-xs leading-5 text-ink-500">
                  Current status: <strong className="text-ink-800">{report.status_label}</strong>. Only
                  valid transitions are offered. Every change is audited.
                </p>
              </div>
              {transitions.length ? (
                <>
                  <div>
                    <label className="label" htmlFor="moderation-status">Next status</label>
                    <select
                      id="moderation-status"
                      className="field"
                      value={nextStatus}
                      onChange={(event) => {
                        setNextStatus(event.target.value);
                        setFeedback(null);
                      }}
                      required
                    >
                      <option value="">Choose a transition…</option>
                      {transitions.map((status) => (
                        <option key={status} value={status}>{statusLabel(status)}</option>
                      ))}
                    </select>
                  </div>
                  {nextStatus === "DUPLICATE" ? (
                    <div>
                      <label className="label" htmlFor="moderation-duplicate">Original report ID</label>
                      <input
                        id="moderation-duplicate"
                        type="text"
                        className="field font-mono text-xs"
                        value={duplicateOf}
                        onChange={(event) => setDuplicateOf(event.target.value)}
                        placeholder="UUID of the original report"
                        required
                      />
                      {allowedDuplicateHints.length ? (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {allowedDuplicateHints.map((hint) => (
                            <button
                              key={hint.id}
                              type="button"
                              className="btn-secondary !px-2 !py-1 text-[0.68rem]"
                              onClick={() => setDuplicateOf(hint.id)}
                            >
                              Use {hint.id.slice(0, 8)} ({formatNumber(hint.distance_m, 0)} m)
                            </button>
                          ))}
                        </div>
                      ) : (
                        <p className="mt-1 text-xs text-ink-400">No nearby duplicate hints are available.</p>
                      )}
                    </div>
                  ) : null}
                  <div>
                    <label className="label" htmlFor="moderation-note">Note (optional)</label>
                    <textarea
                      id="moderation-note"
                      className="field min-h-24 resize-y"
                      maxLength={500}
                      value={note}
                      onChange={(event) => setNote(event.target.value)}
                      placeholder="What evidence or check supports this decision?"
                    />
                    <p className="mt-1 text-xs text-ink-400">Visible to moderators and the reporter, not the public.</p>
                  </div>
                  {feedback ? (
                    <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800" role="status">
                      {feedback}
                    </p>
                  ) : null}
                  {normalizedError ? (
                    <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
                      <p className="font-semibold">{normalizedError.message}</p>
                      {fieldErrors(normalizedError.details).length ? (
                        <ul className="mt-2 list-disc space-y-1 pl-4 text-xs">
                          {fieldErrors(normalizedError.details).map((message) => <li key={message}>{message}</li>)}
                        </ul>
                      ) : null}
                    </div>
                  ) : null}
                  <button type="submit" className="btn-primary w-full" disabled={moderate.isPending}>
                    {moderate.isPending ? <InlineSpinner label="Recording decision" /> : "Record moderation decision"}
                  </button>
                </>
              ) : (
                <p className="text-sm leading-6 text-ink-600">
                  This report is in a terminal status for the current workflow. No further moderation
                  transition is available.
                </p>
              )}
            </form>
          ) : null}

          {user && report.is_owner && !canEdit ? (
            <div className="panel-muted p-4 text-xs leading-5 text-ink-500">
              This report is locked because it is {report.status_label.toLowerCase()}. Locking preserves
              the moderation audit trail. Contact a moderator if something is materially wrong.
            </div>
          ) : null}
        </aside>
      </div>

      <p className="text-xs leading-5 text-ink-500">
        Report identifiers are public; reporter and moderator identities are not. This page does not
        expose a reporter&apos;s email, display name or account profile. For immediate danger call 112.
        <span className="ml-1">Source state: </span>
        <StateBadge state="PARTIAL" className="align-middle" />
      </p>
    </div>
  );
}
