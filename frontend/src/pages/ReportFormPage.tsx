import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { fieldErrors, normalizeError } from "../api/client";
import {
  useArea,
  useAreas,
  useCreateIncident,
  useIncident,
  useUpdateIncident,
} from "../api/queries";
import { useAuth } from "../auth/context";
import { LocationPicker } from "../components/map/CivicMap";
import { DataStateNotice } from "../components/ui/DataState";
import { ErrorState, InlineSpinner, LoadingPanel } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";
import { SectionHeading } from "../components/ui/SectionHeading";
import { INCIDENT_CATEGORIES } from "../lib/constants";
import { formatDate, toLocalInputValue } from "../lib/format";

const MAX_DESCRIPTION = 2000;
const MIN_DESCRIPTION = 10;
const MAX_ATTACHMENTS = 4;

interface FormState {
  area: string;
  category: string;
  description: string;
  occurredAt: string;
  latitude: string;
  longitude: string;
  address: string;
}

const emptyForm: FormState = {
  area: "kolkata",
  category: "waterlogging",
  description: "",
  occurredAt: toLocalInputValue(),
  latitude: "",
  longitude: "",
  address: "",
};

function AuthRequired() {
  return (
    <div className="shell max-w-3xl py-16">
      <div className="panel p-8 text-center">
        <p className="eyebrow">Account required</p>
        <h1 className="display-title mt-2">Sign in to submit a community report</h1>
        <p className="prose-civic mx-auto mt-3 max-w-xl">
          Authentication is required so a report can be attributed internally, edited safely and
          moderated. Your email is never exposed publicly; the public record shows only the report.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link to="/login" className="btn-primary">Log in</Link>
          <Link to="/register" className="btn-secondary">Create an account</Link>
          <Link to="/reports" className="btn-ghost">Back to reports</Link>
        </div>
      </div>
    </div>
  );
}

export function ReportFormPage({ mode }: { mode: "create" | "edit" }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated, user, isLoading: authLoading } = useAuth();
  const areas = useAreas();
  const incident = useIncident(mode === "edit" ? id : undefined);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [files, setFiles] = useState<File[]>([]);
  const [clientError, setClientError] = useState<string | null>(null);

  const areaSlug = form.area || "kolkata";
  const area = useArea(areaSlug);
  const createIncident = useCreateIncident();
  const updateIncident = useUpdateIncident(id ?? "");
  const mutation = mode === "create" ? createIncident : updateIncident;

  useEffect(() => {
    if (mode === "edit" && incident.data) {
      setForm({
        area: incident.data.area.slug,
        category: incident.data.category,
        description: incident.data.description,
        occurredAt: toLocalInputValue(new Date(incident.data.occurred_at)),
        latitude: String(incident.data.latitude),
        longitude: String(incident.data.longitude),
        address: incident.data.address_text,
      });
    }
  }, [mode, incident.data]);

  useEffect(() => {
    if (mode === "create" && areas.data?.length) {
      setForm((current) => (areas.data.some((item) => item.slug === current.area) ? current : {
        ...current,
        area: areas.data[0].slug,
      }));
    }
  }, [areas.data, mode]);

  const minDate = useMemo(() => toLocalInputValue(new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)), []);
  const maxDate = useMemo(() => toLocalInputValue(new Date(Date.now() + 30 * 60 * 1000)), []);
  const point = useMemo(() => {
    const latitude = Number(form.latitude);
    const longitude = Number(form.longitude);
    if (!form.latitude || !form.longitude || Number.isNaN(latitude) || Number.isNaN(longitude)) {
      return null;
    }
    return { latitude, longitude };
  }, [form.latitude, form.longitude]);

  if (authLoading) {
    return <div className="shell py-16"><LoadingPanel label="Checking your session" rows={2} /></div>;
  }
  if (!isAuthenticated) return <AuthRequired />;

  if (mode === "edit") {
    if (incident.isLoading) {
      return <div className="shell py-16"><LoadingPanel label="Loading your report" rows={3} /></div>;
    }
    if (incident.isError) {
      return <div className="shell py-16"><ErrorState error={incident.error} onRetry={() => void incident.refetch()} /></div>;
    }
    if (!incident.data) {
      return (
        <div className="shell max-w-3xl py-16">
          <div className="panel p-8 text-center">
            <p className="font-display text-2xl">Report not found</p>
            <p className="prose-civic mt-2">It may have been removed or is not visible to your account.</p>
            <Link to="/reports" className="btn-secondary mt-5">Back to reports</Link>
          </div>
        </div>
      );
    }
    const canEdit = user?.is_moderator || (incident.data.is_owner && ["SUBMITTED", "UNDER_REVIEW"].includes(incident.data.status));
    if (!canEdit) {
      return (
        <div className="shell max-w-3xl py-16">
          <div className="panel p-8 text-center">
            <p className="font-display text-2xl">This report can no longer be edited</p>
            <p className="prose-civic mx-auto mt-2 max-w-xl">
              Reports can be edited by their owner only while submitted or under review. Verified,
              resolved and rejected records are locked to preserve the moderation trail. Contact a
              moderator if something is materially wrong.
            </p>
            <Link to={`/reports/${incident.data.id}`} className="btn-secondary mt-5">View report</Link>
          </div>
        </div>
      );
    }
  }

  const normalizedError = mutation.isError ? normalizeError(mutation.error) : null;
  const serverFieldErrors = normalizedError ? fieldErrors(normalizedError.details) : [];

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
    setClientError(null);
  }

  function handleFiles(nextFiles: FileList | null) {
    if (!nextFiles) {
      setFiles([]);
      return;
    }
    const selected = Array.from(nextFiles).slice(0, MAX_ATTACHMENTS);
    setFiles(selected);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setClientError(null);
    if (form.description.trim().length < MIN_DESCRIPTION) {
      setClientError(`Describe what you observed in at least ${MIN_DESCRIPTION} characters.`);
      return;
    }
    if (mode === "create" && !point) {
      setClientError("Choose the report location on the map before submitting.");
      return;
    }
    try {
      if (mode === "create") {
        const payload = new FormData();
        payload.append("area", form.area);
        payload.append("category", form.category);
        payload.append("description", form.description.trim());
        payload.append("occurred_at", new Date(form.occurredAt).toISOString());
        payload.append("latitude", String(point?.latitude));
        payload.append("longitude", String(point?.longitude));
        payload.append("address_text", form.address.trim());
        files.forEach((file) => payload.append("attachments", file));
        const created = await createIncident.mutateAsync(payload);
        navigate(`/reports/${created.id}`);
      } else if (incident.data) {
        await updateIncident.mutateAsync({
          category: form.category,
          description: form.description.trim(),
          occurred_at: new Date(form.occurredAt).toISOString(),
          address_text: form.address.trim(),
        });
        navigate(`/reports/${incident.data.id}`);
      }
    } catch {
      // The mutation state renders the normalized API error below.
    }
  }

  return (
    <div className="shell space-y-8 py-10 sm:py-14">
      <PageHeader
        eyebrow={mode === "create" ? "Community · new report" : "Community · edit report"}
        title={mode === "create" ? "Describe what you observed" : "Update your report"}
        description={
          mode === "create"
            ? "Use your own observation, not a copy of a forecast or an official warning. Reports are public, unverified until moderated, and must not contain personal contact details or exact home addresses."
            : "You can correct the description, category, time and coarse location while the report is submitted or under review. The audit history preserves every moderation change."
        }
        aside={<Link to="/reports" className="btn-secondary text-sm">Back to reports</Link>}
      />

      <DataStateNotice
        state="PARTIAL"
        title="Your report is not an official alert"
        reason="A moderator may verify or reject it. Nothing you submit triggers an official warning. Do not use this form for emergencies."
      >
        <p>For immediate danger, call 112 or the relevant emergency service.</p>
      </DataStateNotice>

      <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <form className="panel space-y-5 p-5 sm:p-6" onSubmit={(event) => void handleSubmit(event)} noValidate>
          <SectionHeading eyebrow="Observation" title="What happened?" />

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="report-area">Area</label>
              <select
                id="report-area"
                className="field"
                value={form.area}
                onChange={(event) => update("area", event.target.value)}
                disabled={mode === "edit" || areas.isLoading}
                required
              >
                {(areas.data ?? [{ slug: "kolkata", name: "Kolkata" }]).map((item) => (
                  <option key={item.slug} value={item.slug}>{item.name}</option>
                ))}
              </select>
              {mode === "edit" ? <p className="mt-1 text-xs text-ink-400">Area cannot be changed after submission.</p> : null}
            </div>
            <div>
              <label className="label" htmlFor="report-category">Category</label>
              <select
                id="report-category"
                className="field"
                value={form.category}
                onChange={(event) => update("category", event.target.value)}
                required
              >
                {INCIDENT_CATEGORIES.map((item) => (
                  <option key={item.value} value={item.value}>{item.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="label" htmlFor="report-description">What did you see?</label>
            <textarea
              id="report-description"
              className="field min-h-32 resize-y"
              maxLength={MAX_DESCRIPTION}
              value={form.description}
              onChange={(event) => update("description", event.target.value)}
              placeholder="For example: knee-deep water across the road near the market, blocking the southbound lane."
              required
              aria-describedby="report-description-help"
            />
            <div className="mt-1 flex justify-between gap-2 text-xs text-ink-400">
              <span id="report-description-help">At least {MIN_DESCRIPTION} characters. Describe the observable conditions and location context.</span>
              <span>{form.description.length}/{MAX_DESCRIPTION}</span>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="report-time">When did it occur?</label>
              <input
                id="report-time"
                type="datetime-local"
                className="field"
                value={form.occurredAt}
                min={minDate}
                max={maxDate}
                onChange={(event) => update("occurredAt", event.target.value)}
                required
              />
              <p className="mt-1 text-xs text-ink-400">Reports can cover the last 7 days, not the future.</p>
            </div>
            <div>
              <label className="label" htmlFor="report-address">Coarse landmark (optional)</label>
              <input
                id="report-address"
                type="text"
                className="field"
                maxLength={200}
                value={form.address}
                onChange={(event) => update("address", event.target.value)}
                placeholder="Near a public landmark, not a house number"
              />
              <p className="mt-1 text-xs text-ink-400">Do not enter contact details, names or an exact home address.</p>
            </div>
          </div>

          {mode === "create" ? (
            <>
              <div>
                <p className="label">Location</p>
                <LocationPicker
                  latitude={point?.latitude ?? null}
                  longitude={point?.longitude ?? null}
                  onChange={(latitude, longitude) => {
                    update("latitude", String(latitude));
                    update("longitude", String(longitude));
                  }}
                  boundary={area.data?.boundary}
                  height="360px"
                />
                <div className="mt-2 grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="label" htmlFor="report-lat">Latitude</label>
                    <input
                      id="report-lat"
                      type="number"
                      step="0.000001"
                      min="-90"
                      max="90"
                      className="field"
                      value={form.latitude}
                      onChange={(event) => update("latitude", event.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label className="label" htmlFor="report-lon">Longitude</label>
                    <input
                      id="report-lon"
                      type="number"
                      step="0.000001"
                      min="-180"
                      max="180"
                      className="field"
                      value={form.longitude}
                      onChange={(event) => update("longitude", event.target.value)}
                      required
                    />
                  </div>
                </div>
                <p className="mt-1 text-xs text-ink-400">
                  Coordinates are shown publicly as part of the report. Use the nearest intersection or
                  public landmark, not a private residence.
                </p>
              </div>

              <div>
                <label className="label" htmlFor="report-files">Images (optional, up to {MAX_ATTACHMENTS})</label>
                <input
                  id="report-files"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  multiple
                  className="field"
                  onChange={(event) => handleFiles(event.target.files)}
                />
                <p className="mt-1 text-xs text-ink-400">
                  Only images are accepted. Metadata such as EXIF location is stripped by the server.
                  Do not upload images containing people who have not consented.
                </p>
                {files.length ? (
                  <ul className="mt-2 space-y-1 text-xs text-ink-600">
                    {files.map((file) => (
                      <li key={file.name}>{file.name} · {Math.round(file.size / 1024)} KB</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            </>
          ) : (
            <div className="rounded-xl border border-ink-100 bg-ink-50 p-4">
              <p className="eyebrow">Location</p>
              <p className="mt-2 text-sm text-ink-700">
                {form.latitude && form.longitude
                  ? `${Number(form.latitude).toFixed(5)}, ${Number(form.longitude).toFixed(5)}`
                  : "Location not recorded"}
              </p>
              <p className="mt-1 text-xs text-ink-500">
                Location and attachments cannot be changed after submission. Report a materially
                different location separately.
              </p>
            </div>
          )}

          {clientError ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
              {clientError}
            </div>
          ) : null}

          {normalizedError ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
              <p className="font-semibold">{normalizedError.message}</p>
              {serverFieldErrors.length ? (
                <ul className="mt-2 list-disc space-y-1 pl-4 text-xs">
                  {serverFieldErrors.map((message) => <li key={message}>{message}</li>)}
                </ul>
              ) : null}
            </div>
          ) : null}

          <div className="flex flex-wrap items-center gap-3 border-t border-ink-100 pt-4">
            <button type="submit" className="btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? <InlineSpinner label="Submitting" /> : mode === "create" ? "Submit report" : "Save changes"}
            </button>
            <Link to={mode === "edit" && incident.data ? `/reports/${incident.data.id}` : "/reports"} className="btn-ghost">
              Cancel
            </Link>
          </div>
        </form>

        <aside className="space-y-4">
          <div className="panel p-5 sm:p-6">
            <p className="eyebrow">Before you submit</p>
            <ul className="mt-3 space-y-3 text-sm leading-6 text-ink-600">
              <li><strong className="text-ink-900">Use your own observation.</strong> Do not copy a forecast, warning or social-media claim.</li>
              <li><strong className="text-ink-900">Be specific but safe.</strong> Describe what is visible and where, without exposing a private address or personal details.</li>
              <li><strong className="text-ink-900">Expect moderation.</strong> New reports start as unverified. A moderator can mark under review, verified, resolved, rejected, expired or duplicate.</li>
              <li><strong className="text-ink-900">Duplicates are a hint.</strong> The system may show nearby reports, but never merges them automatically.</li>
            </ul>
          </div>

          <div className="panel-muted p-5">
            <p className="eyebrow">What the public sees</p>
            <p className="prose-civic mt-2">
              The public sees the description, category, status, verification label, coarse location,
              coordinates, attachments and the moderation history. It never sees your email address or
              identity. Moderator identities are not exposed either.
            </p>
          </div>

          {mode === "edit" && incident.data ? (
            <div className="panel p-5">
              <p className="eyebrow">Current status</p>
              <p className="mt-2 text-sm font-semibold text-ink-900">{incident.data.status_label}</p>
              <p className="mt-1 text-xs text-ink-500">Submitted {formatDate(incident.data.created_at)}</p>
              <Link to={`/reports/${incident.data.id}`} className="link mt-2 inline-block text-xs">
                View public report and audit history
              </Link>
            </div>
          ) : null}
        </aside>
      </div>
    </div>
  );
}
