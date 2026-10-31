import { CircleCheck, Clock, Navigation, OctagonAlert, Trash2, TriangleAlert } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { CircleMarker, Polyline, useMap, useMapEvents } from "react-leaflet";
import { Link } from "react-router-dom";

import { fieldErrors, normalizeError } from "../api/client";
import { api } from "../api/client";
import type { PickedPlace, RoutePlan } from "../api/types";
import { MyPlaces } from "../components/place/MyPlaces";
import { PlacePicker } from "../components/place/PlacePicker";
import { useCreateRoute, useDeleteRoute, useRoutes, useRouteStatus, useUpdateRoute } from "../api/queries";
import type { RouteStatus, SavedRoute } from "../api/types";
import { useAuth } from "../auth/context";
import { CivicMap } from "../components/map/CivicMap";
import { ErrorState, InlineSpinner, LoadingPanel } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";
import { TRUST_META } from "../lib/constants";
import { cn, formatRelative } from "../lib/format";
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

const ROUTE_STATE = {
  serious_reports: { title: "Serious problems reported", icon: OctagonAlert },
  reports: { title: "Reports on your route", icon: TriangleAlert },
  no_reports: { title: "No reports on your route", icon: CircleCheck },
};

function FitRoute({ points }: { points: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    map.fitBounds(points, { padding: [16, 16] });
  }, [map, points]);
  return null;
}

function RouteCard({ route }: { route: SavedRoute }) {
  const { t } = useT();
  const status = useRouteStatus(route.id);
  const remove = useDeleteRoute();
  const update = useUpdateRoute();
  const data = status.data;
  const state = data ? ROUTE_STATE[data.summary] : null;
  const Icon = state?.icon;

  return (
    <article className={cn("overflow-hidden rounded-2xl border", data ? SUMMARY_TONE[data.summary] : "border-ink-100 bg-white")}>
      <CivicMap height="130px" zoom={12} attribution={false}>
        <FitRoute points={route.points} />
        <Polyline positions={route.points} pathOptions={{ color: "#1f8a78", weight: 4 }} />
      </CivicMap>
      <div className="p-4">
        <div className="flex items-start justify-between gap-2">
          <h2 data-original-text className="font-display text-lg text-ink-950">{route.label}</h2>
          <button
            type="button"
            className="rounded p-1 text-ink-500 hover:bg-ink-100"
            aria-label="Delete route"
            disabled={remove.isPending}
            onClick={() => remove.mutate(route.id)}
          >
            <Trash2 className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
        {status.isError ? (
          <p className="mt-2 text-sm text-red-800">Couldn't check this route. Try again shortly.</p>
        ) : !data || !state || !Icon ? (
          <p className="mt-2 text-sm text-ink-500">Checking…</p>
        ) : (
          <div className="mt-2 space-y-3 text-sm text-ink-800">
            <p className="flex items-center gap-2 font-semibold text-ink-950">
              <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
              {state.title}
            </p>
            {data.official_alerts ? (
              <Link to="/alerts" className="block font-semibold text-red-900 underline">{`Official warnings in effect: ${data.official_alerts}`}</Link>
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
                      {TRUST_META[report.trust].label} · {formatRelative(report.occurred_at)} · {`${report.distance_m} m from your route`}
                    </span>
                  </li>
                ))}
              </ul>
            ) : null}
            <dl className="grid grid-cols-3 gap-2 text-center">
              <div className="rounded-xl bg-white/60 p-2 dark:bg-ink-50">
                <dt className="text-[0.68rem] text-ink-600">Distance</dt>
                <dd className="font-semibold text-ink-950">{`${data.distance_km} km`}</dd>
              </div>
              <div className="rounded-xl bg-white/60 p-2 dark:bg-ink-50">
                <dt className="text-[0.68rem] text-ink-600">Rain now</dt>
                <dd className="font-semibold text-ink-950">{data.rain_chance_now_pct === null ? "—" : `${data.rain_chance_now_pct}%`}</dd>
              </div>
              <div className="rounded-xl bg-white/60 p-2 dark:bg-ink-50">
                <dt className="text-[0.68rem] text-ink-600">When you leave</dt>
                <dd className="font-semibold text-ink-950">{data.rain_chance_leaving_pct === null ? "—" : `${data.rain_chance_leaving_pct}%`}</dd>
              </div>
            </dl>
            <label className="flex items-center justify-between gap-2 text-xs text-ink-700">
              <span className="inline-flex items-center gap-1.5">
                <Clock className="h-4 w-4" aria-hidden="true" />
                {t("I usually leave at")}
              </span>
              <input
                type="time"
                className="field !w-auto !py-1 text-xs"
                defaultValue={route.leave_at?.slice(0, 5) ?? ""}
                onBlur={(event) => update.mutate({ id: route.id, leave_at: event.target.value || null })}
              />
            </label>
          </div>
        )}
      </div>
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
        description="Check your usual trips before you leave: reports along the way, and the chance of rain."
      />
      <div className="space-y-5">
        <div className="grid gap-4 md:grid-cols-2">
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
