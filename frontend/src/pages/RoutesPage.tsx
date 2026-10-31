import { Navigation } from "lucide-react";
import { useState, type FormEvent } from "react";
import { CircleMarker, Polyline, useMapEvents } from "react-leaflet";
import { Link } from "react-router-dom";

import { fieldErrors, normalizeError } from "../api/client";
import { api } from "../api/client";
import type { PickedPlace, RoutePlan } from "../api/types";
import { MyPlaces } from "../components/place/MyPlaces";
import { PlacePicker } from "../components/place/PlacePicker";
import { useCreateRoute, useDeleteRoute, useRoutes, useRouteStatus } from "../api/queries";
import type { RouteStatus, SavedRoute } from "../api/types";
import { useAuth } from "../auth/context";
import { CivicMap } from "../components/map/CivicMap";
import { ErrorState, InlineSpinner, LoadingPanel } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";
import { TRUST_META } from "../lib/constants";
import { cn, formatRelative, formatTime, formatWithUnit } from "../lib/format";
import { useT } from "../lib/i18n";

const MAX_POINTS = 12;
const LINE_COLOR = "#243733";

const SUMMARY_TONE: Record<RouteStatus["summary"], string> = {
  serious_reports: "border-red-200 bg-red-50",
  reports: "border-amber-200 bg-amber-50",
  no_reports: "border-ink-100 bg-white",
};

function DrawHandler({ onAdd }: { onAdd: (point: [number, number]) => void }) {
  useMapEvents({
    click(event) {
      onAdd([Number(event.latlng.lat.toFixed(5)), Number(event.latlng.lng.toFixed(5))]);
    },
  });
  return null;
}

function RouteCard({ route }: { route: SavedRoute }) {
  const { t } = useT();
  const status = useRouteStatus(route.id);
  const remove = useDeleteRoute();
  const data = status.data;

  return (
    <article className={cn("rounded-2xl border p-4", data ? SUMMARY_TONE[data.summary] : "border-ink-100 bg-white")}>
      <div className="flex items-start justify-between gap-2">
        <h2 className="font-display text-lg text-ink-950">{route.label}</h2>
        <button
          type="button"
          className="text-xs text-ink-500 underline"
          disabled={remove.isPending}
          onClick={() => remove.mutate(route.id)}
        >
          Delete
        </button>
      </div>
      {status.isError ? (
        <p className="mt-2 text-sm text-red-800">Couldn't check this route. Try again shortly.</p>
      ) : !data ? (
        <p className="mt-2 text-sm text-ink-500">Checking…</p>
      ) : (
        <div className="mt-2 space-y-2 text-sm text-ink-800">
          {data.official_alerts ? (
            <p className="font-semibold text-red-900">
              <Link to="/alerts" className="underline">{data.official_alerts} official warning(s) in effect</Link>
            </p>
          ) : null}
          {data.reports.length ? (
            <ul className="space-y-2">
              {data.reports.map((report) => (
                <li key={report.id}>
                  <Link to={`/reports/${report.id}`} className="underline">{report.category_label}</Link>
                  {report.place ? ` · ${report.place}` : ""}
                  {report.water_depth_label ? ` · ${report.water_depth_label}` : ""}
                  {report.passability_label ? ` · ${report.passability_label}` : ""}
                  <span className="block text-xs text-ink-600">
                    {TRUST_META[report.trust].label} · {formatRelative(report.occurred_at)} · {report.distance_m} m from your route
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p>{t("No active reports along this route. That does not mean the road is clear.")}</p>
          )}
          <p className="text-xs text-ink-600">
            {t("Rain, next 2 hours")}:{" "}
            {data.rain.total_mm === null ? t("Not available") : formatWithUnit(data.rain.total_mm, "mm")}
            {data.rain.next_rain_at ? ` · ${t("Rain likely around {time}", { time: formatTime(data.rain.next_rain_at) })}` : ""}
          </p>
        </div>
      )}
    </article>
  );
}

function NewRoute() {
  const { t } = useT();
  const create = useCreateRoute();
  const [label, setLabel] = useState("");
  const [leaveAt, setLeaveAt] = useState("");
  const [from, setFrom] = useState<PickedPlace | null>(null);
  const [to, setTo] = useState<PickedPlace | null>(null);
  const [finding, setFinding] = useState(false);
  const [points, setPoints] = useState<[number, number][]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const apiError = create.isError ? normalizeError(create.error) : null;

  async function findRoute() {
    if (!from || !to) return;
    setFinding(true);
    setMessage(null);
    if (!label.trim()) setLabel(`${from.label} to ${to.label}`.slice(0, 80));
    try {
      const response = await api.post<RoutePlan>("/routes/plan/", {
        origin: [from.latitude, from.longitude],
        destination: [to.latitude, to.longitude],
      });
      setPoints(response.data.points);
    } catch {
      setPoints([[from.latitude, from.longitude], [to.latitude, to.longitude]]);
      setMessage("Road directions aren't available right now, so this is a straight line. Tap the map to add your turns.");
    } finally {
      setFinding(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!label.trim() || points.length < 2) {
      setMessage("Name the route and tap at least two points on the map.");
      return;
    }
    setMessage(null);
    try {
      await create.mutateAsync({ label: label.trim(), points, leave_at: leaveAt || null });
      setLabel("");
      setLeaveAt("");
      setPoints([]);
    } catch {
      // The mutation state renders the API error below.
    }
  }

  return (
    <form className="panel space-y-3 p-4" onSubmit={(event) => void submit(event)} noValidate>
      <h2 className="font-display text-lg text-ink-950">Add a route</h2>
      <p className="text-xs leading-5 text-ink-600">
        Tap along the roads you use, from start to end. Add a point at each major turn. Routes are private.
      </p>
      <div>
        <label className="label" htmlFor="route-name">Name</label>
        <input
          id="route-name"
          className="field"
          maxLength={80}
          value={label}
          onChange={(event) => setLabel(event.target.value)}
          placeholder="Home to college"
        />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <PlacePicker label="From" placeholder="Home, or type a place" value={from} onPick={setFrom} />
        <PlacePicker label="To" placeholder="College, or type a place" value={to} onPick={setTo} />
      </div>
      <button type="button" className="btn-secondary w-full" disabled={!from || !to || finding} onClick={() => void findRoute()}>
        <Navigation className="mr-1.5 h-4 w-4" aria-hidden="true" />
        {finding ? "Finding route…" : "Find route"}
      </button>
      <div>
        <label className="label" htmlFor="route-leave">When do you usually leave? (optional)</label>
        <input id="route-leave" type="time" className="field" value={leaveAt} onChange={(event) => setLeaveAt(event.target.value)} />
        <p className="mt-1 text-xs text-ink-500">If rain is likely near that time, we'll tell you up to 2 hours before.</p>
      </div>
      <CivicMap height="320px" zoom={12}>
        <DrawHandler onAdd={(point) => setPoints((current) => (current.length < MAX_POINTS ? [...current, point] : current))} />
        {points.length > 1 ? <Polyline positions={points} pathOptions={{ color: LINE_COLOR, weight: 4 }} /> : null}
        {points.map((point, index) => (
          <CircleMarker
            key={`${point[0]}-${point[1]}-${index}`}
            center={point}
            radius={5}
            pathOptions={{ color: "#ffffff", weight: 1.5, fillColor: LINE_COLOR, fillOpacity: 1 }}
          />
        ))}
      </CivicMap>
      <div className="flex items-center justify-between text-xs text-ink-600">
        <span>{points.length > MAX_POINTS ? "Route found" : `${points.length} of ${MAX_POINTS} points`}</span>
        <button type="button" className="underline" onClick={() => setPoints((current) => current.slice(0, -1))} disabled={!points.length}>
          Undo last point
        </button>
      </div>
      {message ? <p className="text-sm text-red-800" role="alert">{message}</p> : null}
      {apiError ? (
        <p className="text-sm text-red-800" role="alert">
          {fieldErrors(apiError.details)[0] ?? apiError.message}
        </p>
      ) : null}
      <button type="submit" className="btn-primary w-full" disabled={create.isPending}>
        {create.isPending ? <InlineSpinner label="Saving" /> : t("Save route")}
      </button>
    </form>
  );
}

export function RoutesPage() {
  const { t } = useT();
  const { isAuthenticated, isLoading } = useAuth();
  const routes = useRoutes(isAuthenticated);

  if (isLoading) return <div className="shell py-12"><LoadingPanel label="Checking your session" rows={2} /></div>;
  if (!isAuthenticated) {
    return (
      <div className="shell max-w-xl py-12 text-center">
        <h1 className="display-title">{t("My routes")}</h1>
        <p className="prose-civic mt-2">Save your commute to see reports along it and get alerts before you leave.</p>
        <Link to="/login?next=/routes" className="btn-primary mt-4">{t("Log in")}</Link>
      </div>
    );
  }

  return (
    <div className="shell space-y-5 py-6 sm:py-10">
      <PageHeader
        eyebrow="Commute"
        title={t("My routes")}
        description="Reports within 300 m of the line you draw, plus rain in the next two hours."
      />
      <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">
        <div className="space-y-3">
          {routes.isError ? (
            <ErrorState error={routes.error} onRetry={() => void routes.refetch()} />
          ) : routes.isLoading ? (
            <LoadingPanel label="Loading your routes" rows={2} />
          ) : routes.data?.length ? (
            routes.data.map((route) => <RouteCard key={route.id} route={route} />)
          ) : (
            <p className="panel p-4 text-sm text-ink-700">No routes yet. Add your first one, such as home to college.</p>
          )}
        </div>
        <MyPlaces />
      <NewRoute />
      </div>
    </div>
  );
}
