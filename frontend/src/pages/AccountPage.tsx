import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { fieldErrors, normalizeError } from "../api/client";
import {
  useArea,
  useAreas,
  useCreateSavedLocation,
  useDeleteSavedLocation,
  useIncidents,
  useMe,
  useSavedLocations,
  useUpdateMe,
  useUpdatePreferences,
} from "../api/queries";
import { useAuth } from "../auth/context";
import { AlertSettings } from "../components/account/AlertSettings";
import { LocationPicker } from "../components/map/CivicMap";
import { StateBadge } from "../components/ui/DataState";
import { EmptyState, ErrorState, InlineSpinner, LoadingPanel } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";
import { SectionHeading } from "../components/ui/SectionHeading";
import { formatDate, formatDateTime, titleCase } from "../lib/format";

function Feedback({ message, tone }: { message: string; tone: "success" | "error" }) {
  return (
    <p
      className={
        tone === "success"
          ? "rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800"
          : "rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800"
      }
      role={tone === "error" ? "alert" : "status"}
    >
      {message}
    </p>
  );
}

function AccountContent() {
  const { user, updateUser, logout } = useAuth();
  const me = useMe();
  const areas = useAreas();
  const area = useArea();
  const savedLocations = useSavedLocations();
  const myReports = useIncidents({ mine: true });
  const updateMe = useUpdateMe();
  const updatePreferences = useUpdatePreferences();
  const createSavedLocation = useCreateSavedLocation();
  const deleteSavedLocation = useDeleteSavedLocation();

  const current = me.data ?? user;
  const [displayName, setDisplayName] = useState(current?.display_name ?? "");
  const [temperatureUnit, setTemperatureUnit] = useState<"C" | "F">(
    current?.preferences.temperature_unit ?? "C",
  );
  const [defaultArea, setDefaultArea] = useState(current?.preferences.default_area ?? "");
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [preferenceMessage, setPreferenceMessage] = useState<string | null>(null);
  const [savedError, setSavedError] = useState<string | null>(null);
  const [savedLabel, setSavedLabel] = useState("");
  const [savedArea, setSavedArea] = useState("kolkata");
  const [savedPoint, setSavedPoint] = useState<{ latitude: number; longitude: number } | null>(null);

  if (me.isLoading && !current) {
    return <div className="shell py-16"><LoadingPanel label="Loading your account" rows={3} /></div>;
  }
  if (me.isError) {
    return (
      <div className="shell py-16">
        <ErrorState error={me.error} onRetry={() => void me.refetch()} />
      </div>
    );
  }
  if (!current) return null;

  async function handleProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setProfileMessage(null);
    if (displayName.trim().length < 2) {
      setProfileMessage("Display name must have at least 2 characters.");
      return;
    }
    try {
      const updated = await updateMe.mutateAsync({ display_name: displayName.trim() });
      updateUser(updated);
      setProfileMessage("Display name updated.");
    } catch {
      // Render the mutation error below.
    }
  }

  async function handlePreferences(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPreferenceMessage(null);
    try {
      const updated = await updatePreferences.mutateAsync({
        temperature_unit: temperatureUnit,
        default_area: defaultArea || null,
      });
      updateUser(updated);
      setPreferenceMessage("Preferences saved.");
    } catch {
      // Render the mutation error below.
    }
  }

  async function handleSavedLocation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavedError(null);
    if (!savedLabel.trim()) {
      setSavedError("Give the saved location a short private label.");
      return;
    }
    if (!savedPoint) {
      setSavedError("Choose a point on the map.");
      return;
    }
    try {
      await createSavedLocation.mutateAsync({
        label: savedLabel.trim(),
        area: savedArea || null,
        latitude: savedPoint.latitude,
        longitude: savedPoint.longitude,
      });
      setSavedLabel("");
      setSavedPoint(null);
    } catch {
      // Render the mutation error below.
    }
  }

  const profileError = updateMe.isError ? normalizeError(updateMe.error) : null;
  const preferenceError = updatePreferences.isError ? normalizeError(updatePreferences.error) : null;
  const savedMutationError = createSavedLocation.isError ? normalizeError(createSavedLocation.error) : null;
  const savedDeleteError = deleteSavedLocation.isError ? normalizeError(deleteSavedLocation.error) : null;

  return (
    <div className="space-y-12">
      <AlertSettings user={current} />
      <section className="grid gap-6 lg:grid-cols-[1fr_0.8fr]">
        <form className="panel space-y-4 p-5 sm:p-6" onSubmit={(event) => void handleProfile(event)}>
          <SectionHeading eyebrow="Profile" title="Your account" />
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">Email</dt>
              <dd className="mt-1 font-medium text-ink-900">{current.email}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">Role</dt>
              <dd className="mt-1 font-medium text-ink-900">
                {current.is_moderator ? "Moderator" : titleCase(current.role)}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">Joined</dt>
              <dd className="mt-1 text-ink-700">{formatDate(current.date_joined)}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">Email visibility</dt>
              <dd className="mt-1 text-ink-700">Private — never exposed on public reports</dd>
            </div>
          </dl>
          <div>
            <label className="label" htmlFor="account-name">Display name</label>
            <input
              id="account-name"
              type="text"
              className="field"
              maxLength={80}
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              required
            />
            <p className="mt-1 text-xs text-ink-400">Used for account navigation only.</p>
          </div>
          {profileMessage ? <Feedback message={profileMessage} tone="success" /> : null}
          {profileError ? (
            <Feedback
              tone="error"
              message={[profileError.message, ...fieldErrors(profileError.details)].join(" ")}
            />
          ) : null}
          <div className="flex flex-wrap items-center gap-3">
            <button type="submit" className="btn-primary" disabled={updateMe.isPending}>
              {updateMe.isPending ? <InlineSpinner label="Saving" /> : "Save profile"}
            </button>
            <button type="button" className="btn-ghost" onClick={() => void logout()}>
              Log out
            </button>
          </div>
        </form>

        <form className="panel space-y-4 p-5 sm:p-6" onSubmit={(event) => void handlePreferences(event)}>
          <SectionHeading
            eyebrow="Preferences"
            title="Display units"
            description="Temperature units apply across public weather, heat and climate displays."
          />
          <div>
            <label className="label" htmlFor="account-unit">Temperature unit</label>
            <select
              id="account-unit"
              className="field"
              value={temperatureUnit}
              onChange={(event) => setTemperatureUnit(event.target.value as "C" | "F")}
            >
              <option value="C">Celsius (°C)</option>
              <option value="F">Fahrenheit (°F)</option>
            </select>
          </div>
          <div>
            <label className="label" htmlFor="account-area">Default area</label>
            <select
              id="account-area"
              className="field"
              value={defaultArea}
              onChange={(event) => setDefaultArea(event.target.value)}
            >
              <option value="">No default</option>
              {(areas.data ?? []).map((item) => (
                <option key={item.slug} value={item.slug}>{item.name}</option>
              ))}
            </select>
          </div>
          {preferenceMessage ? <Feedback message={preferenceMessage} tone="success" /> : null}
          {preferenceError ? (
            <Feedback
              tone="error"
              message={[preferenceError.message, ...fieldErrors(preferenceError.details)].join(" ")}
            />
          ) : null}
          <button type="submit" className="btn-secondary" disabled={updatePreferences.isPending}>
            {updatePreferences.isPending ? <InlineSpinner label="Saving" /> : "Save preferences"}
          </button>
        </form>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <div>
          <SectionHeading
            eyebrow="Private"
            title="Saved locations"
            description="Up to 20 private locations. They are visible only to your account and are never published with reports."
          />
          {savedDeleteError ? (
            <Feedback
              tone="error"
              message={[savedDeleteError.message, ...fieldErrors(savedDeleteError.details)].join(" ")}
            />
          ) : null}
          {savedLocations.isLoading ? (
            <div className="mt-4"><LoadingPanel label="Loading saved locations" rows={2} /></div>
          ) : savedLocations.isError ? (
            <ErrorState className="mt-4" error={savedLocations.error} onRetry={() => void savedLocations.refetch()} />
          ) : savedLocations.data?.length ? (
            <ul className="mt-4 space-y-3">
              {savedLocations.data.map((location) => (
                <li key={location.id} className="panel flex flex-wrap items-center justify-between gap-3 p-4">
                  <div>
                    <p className="text-sm font-semibold text-ink-900">{location.label}</p>
                    <p className="mt-0.5 text-xs text-ink-500">
                      {location.latitude.toFixed(5)}, {location.longitude.toFixed(5)}
                      {location.area ? ` · ${location.area}` : ""} · added {formatDate(location.created_at)}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn-ghost text-xs text-red-700"
                    disabled={deleteSavedLocation.isPending}
                    onClick={() => {
                      if (window.confirm(`Remove “${location.label}” from your saved locations?`)) {
                        void deleteSavedLocation.mutateAsync(location.id);
                      }
                    }}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="panel-muted mt-4 p-5">
              <p className="text-sm font-medium text-ink-800">No saved locations</p>
              <p className="mt-1 text-xs leading-5 text-ink-500">
                Add a private reference point with the form beside this list.
              </p>
            </div>
          )}
        </div>

        <form className="panel space-y-4 p-5 sm:p-6" onSubmit={(event) => void handleSavedLocation(event)}>
          <SectionHeading eyebrow="Add" title="Save a private location" />
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="saved-label">Label</label>
              <input
                id="saved-label"
                type="text"
                className="field"
                maxLength={80}
                value={savedLabel}
                onChange={(event) => setSavedLabel(event.target.value)}
                placeholder="Home area, workplace…"
                required
              />
            </div>
            <div>
              <label className="label" htmlFor="saved-area">Area</label>
              <select
                id="saved-area"
                className="field"
                value={savedArea}
                onChange={(event) => setSavedArea(event.target.value)}
              >
                <option value="">No area</option>
                {(areas.data ?? []).map((item) => (
                  <option key={item.slug} value={item.slug}>{item.name}</option>
                ))}
              </select>
            </div>
          </div>
          <LocationPicker
            latitude={savedPoint?.latitude ?? null}
            longitude={savedPoint?.longitude ?? null}
            onChange={(latitude, longitude) => setSavedPoint({ latitude, longitude })}
            boundary={area.data?.boundary}
            height="280px"
          />
          {savedError ? <Feedback message={savedError} tone="error" /> : null}
          {savedMutationError ? (
            <Feedback
              tone="error"
              message={[savedMutationError.message, ...fieldErrors(savedMutationError.details)].join(" ")}
            />
          ) : null}
          <button type="submit" className="btn-secondary" disabled={createSavedLocation.isPending}>
            {createSavedLocation.isPending ? <InlineSpinner label="Saving" /> : "Save location"}
          </button>
        </form>
      </section>

      <section>
        <SectionHeading
          eyebrow="Your reports"
          title="Reports submitted by this account"
          description="Private visibility rules still apply. Rejected, duplicate and expired reports remain visible to you with their moderation history."
          action={<Link to="/reports/new" className="btn-primary text-sm">Submit a report</Link>}
        />
        {myReports.isLoading ? (
          <div className="mt-5"><LoadingPanel label="Loading your reports" /></div>
        ) : myReports.isError ? (
          <ErrorState className="mt-5" error={myReports.error} onRetry={() => void myReports.refetch()} />
        ) : myReports.data?.results.length ? (
          <ul className="mt-5 space-y-3">
            {myReports.data.results.map((incident) => (
              <li key={incident.id}>
                <Link
                  to={`/reports/${incident.id}`}
                  className="panel flex flex-wrap items-start justify-between gap-4 p-4 transition hover:border-ink-200"
                >
                  <div className="min-w-0">
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
                      <span className="chip border-ink-200 bg-white text-ink-600">{incident.status_label}</span>
                      {!incident.is_public ? (
                        <span className="chip border-ink-200 bg-ink-50 text-ink-600">Not public</span>
                      ) : null}
                    </div>
                    <p className="mt-2 text-sm leading-6 text-ink-600">{incident.description}</p>
                    <p className="mt-1 text-xs text-ink-500">
                      Occurred {formatDateTime(incident.occurred_at)} · submitted {formatDate(incident.created_at)}
                    </p>
                  </div>
                  <span className="text-xs font-semibold text-ink-700">Open report →</span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState
            className="mt-5"
            title="You have not submitted a report"
            description="Community reports are optional. If you submit one, its moderation state and audit history will appear here."
            action={<Link to="/reports/new" className="btn-secondary text-sm">Submit your first report</Link>}
          />
        )}
      </section>

      <div className="panel-muted flex flex-wrap items-center justify-between gap-3 p-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Account data</p>
          <p className="mt-1 text-xs leading-5 text-ink-500">
            Saved locations and preferences are private. Public reports never include your email or
            display name. There is no automated data-export or deletion flow in this prototype.
          </p>
        </div>
        <StateBadge state={myReports.data ? "AVAILABLE" : "PARTIAL"} />
      </div>
    </div>
  );
}

export function AccountPage() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div className="shell py-16"><LoadingPanel label="Checking your session" rows={2} /></div>;
  }

  if (!isAuthenticated) {
    return (
      <div className="shell max-w-3xl py-16">
        <div className="panel p-8 text-center">
          <p className="eyebrow">Account required</p>
          <h1 className="display-title mt-2">Sign in to manage your account</h1>
          <p className="prose-civic mx-auto mt-3 max-w-xl">
            Profile, preferences, saved locations and your submitted reports are visible only to you.
            Public data remains available without an account.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link to="/login?next=/account" className="btn-primary">Log in</Link>
            <Link to="/register" className="btn-secondary">Create an account</Link>
            <Link to="/" className="btn-ghost">Back to overview</Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="shell space-y-6 py-5 sm:py-8">
      <PageHeader
        eyebrow="Account"
        title="Your ClimateSense account"
        description="Manage the private details attached to your reports. Your identity is never part of the public record."
      />
      <AccountContent />
    </div>
  );
}
