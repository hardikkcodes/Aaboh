import { useState, type FormEvent } from "react";
import { CircleMarker, Popup } from "react-leaflet";
import { Link } from "react-router-dom";

import { fieldErrors, normalizeError } from "../api/client";
import { useCreateSpot, useDeleteSpot, useSpots } from "../api/queries";
import { useAuth } from "../auth/context";
import { CivicMap, LocationPicker } from "../components/map/CivicMap";
import { ErrorState, EmptyState, InlineSpinner, LoadingPanel } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";
import { useT } from "../lib/i18n";

const KINDS = [
  { value: "cool_shade", label: "Cool or shaded place", color: "#0891b2" },
  { value: "drinking_water", label: "Drinking water", color: "#2563eb" },
  { value: "shelter", label: "Rain or storm shelter", color: "#7c3aed" },
];

function AddSpot() {
  const create = useCreateSpot();
  const [kind, setKind] = useState("cool_shade");
  const [name, setName] = useState("");
  const [point, setPoint] = useState<{ latitude: number; longitude: number } | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const apiError = create.isError ? normalizeError(create.error) : null;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim() || !point) {
      setMessage("Add a name and tap the place on the map.");
      return;
    }
    setMessage(null);
    try {
      await create.mutateAsync({ kind, name: name.trim(), ...point });
      setName("");
      setPoint(null);
    } catch {
      // The mutation state renders the API error below.
    }
  }

  return (
    <form className="panel space-y-3 p-4" onSubmit={(event) => void submit(event)} noValidate>
      <h2 className="section-title">Add a public place</h2>
      <div>
        <label className="label" htmlFor="spot-kind">Type</label>
        <select id="spot-kind" className="field" value={kind} onChange={(event) => setKind(event.target.value)}>
          {KINDS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
        </select>
      </div>
      <div>
        <label className="label" htmlFor="spot-name">Name</label>
        <input id="spot-name" className="field" maxLength={120} value={name} onChange={(event) => setName(event.target.value)} />
        <p className="mt-1 text-xs text-ink-500">Public places only, never a private home.</p>
      </div>
      <LocationPicker
        latitude={point?.latitude ?? null}
        longitude={point?.longitude ?? null}
        onChange={(latitude, longitude) => setPoint({ latitude, longitude })}
        height="240px"
      />
      {message ? <p className="text-sm text-red-800" role="alert">{message}</p> : null}
      {apiError ? (
        <p className="text-sm text-red-800" role="alert">{fieldErrors(apiError.details)[0] ?? apiError.message}</p>
      ) : null}
      <button type="submit" className="btn-primary w-full" disabled={create.isPending}>
        {create.isPending ? <InlineSpinner label="Saving" /> : "Add place"}
      </button>
    </form>
  );
}

export function SpotsPage() {
  const { t } = useT();
  const { isAuthenticated, isModerator } = useAuth();
  const spots = useSpots();
  const remove = useDeleteSpot();
  const items = spots.data ?? [];

  return (
    <div className="shell space-y-5 py-5 sm:py-8">
      <PageHeader
        title={t("Cool spots")}
        description="Shade, drinking water and shelter added by residents. Check a place is open before relying on it."
      />
      <div className="grid gap-5 lg:grid-cols-[1.3fr_1fr]">
        <div className="space-y-3">
          <CivicMap height="360px" zoom={12}>
            {items.map((spot) => (
              <CircleMarker
                key={spot.id}
                center={[spot.latitude, spot.longitude]}
                radius={8}
                pathOptions={{
                  color: "#ffffff",
                  weight: 2,
                  fillColor: KINDS.find((kind) => kind.value === spot.kind)?.color,
                  fillOpacity: 0.95,
                }}
              >
                <Popup>
                  <p className="font-semibold">{spot.name}</p>
                  <p className="text-xs">{spot.kind_label}</p>
                </Popup>
              </CircleMarker>
            ))}
          </CivicMap>
          {spots.isError ? (
            <ErrorState error={spots.error} onRetry={() => void spots.refetch()} />
          ) : spots.isLoading ? (
            <LoadingPanel label="Loading places" rows={2} />
          ) : items.length ? (
            <ul className="space-y-2">
              {items.map((spot) => (
                <li key={spot.id} className="panel flex items-center justify-between gap-3 p-3 text-sm">
                  <span>
                    <span className="block font-medium text-ink-900">{spot.name}</span>
                    <span className="text-xs text-ink-500">{spot.kind_label}</span>
                  </span>
                  {spot.is_owner || isModerator ? (
                    <button type="button" className="text-xs text-ink-500 underline" onClick={() => remove.mutate(spot.id)}>
                      Remove
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No places added yet" description="Be the first to add a shaded park, a public tap or a shelter." />
          )}
        </div>
        {isAuthenticated ? (
          <AddSpot />
        ) : (
          <div className="panel p-4 text-sm text-ink-700">
            <Link to="/login?next=/spots" className="font-semibold underline">{t("Log in")}</Link> to add a place.
          </div>
        )}
      </div>
    </div>
  );
}
