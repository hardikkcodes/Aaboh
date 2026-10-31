import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../../api/client";
import type { NearestPlaceResponse, SavedLocation } from "../../api/types";
import { useCreateSavedLocation, useDeleteSavedLocation, useSavedLocations } from "../../api/queries";
import { useAuth } from "../../auth/context";
import { placePath } from "../../lib/place";

/**
 * Private saved map points. A saved label is resolved to the nearest published
 * locality on click; coordinates are never displayed or treated as an address.
 */
export function SavedPlaces({ className }: { className?: string }) {
  const { isAuthenticated } = useAuth();
  const saved = useSavedLocations(isAuthenticated);
  const remove = useDeleteSavedLocation();
  const navigate = useNavigate();
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  if (!isAuthenticated || !saved.data?.length) return null;

  async function open(location: SavedLocation) {
    setMessage(null);
    setBusyId(location.id);
    try {
      const response = await api.get<NearestPlaceResponse>("/locations/nearest/", {
        params: { lat: location.latitude, lon: location.longitude },
      });
      const nearest = response.data.place;
      if (!nearest) {
        setMessage(`No covered locality was found near “${location.label}”.`);
        return;
      }
      navigate(placePath(nearest), {
        state: { fromSavedPlace: location.label, distanceKm: nearest.distance_km },
      });
    } catch {
      setMessage(`Could not open “${location.label}”. Try again.`);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className={className}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-ink-500">Saved:</span>
        {saved.data.slice(0, 8).map((location) => (
          <span
            key={location.id}
            className="inline-flex items-center gap-1 rounded-full border border-ink-200 bg-white pl-2.5 pr-1 text-xs"
          >
            <button
              type="button"
              onClick={() => void open(location)}
              disabled={busyId === location.id}
              className="py-1 font-medium text-ink-800 hover:underline disabled:opacity-60"
            >
              {busyId === location.id ? `${location.label}…` : location.label}
            </button>
            <button
              type="button"
              aria-label={`Remove saved place ${location.label}`}
              title="Remove saved place"
              onClick={() => remove.mutate(location.id)}
              className="rounded-full px-1 text-ink-400 hover:bg-ink-100 hover:text-ink-700"
            >
              ×
            </button>
          </span>
        ))}
        {saved.data.length > 8 ? <span className="text-xs text-ink-500">+{saved.data.length - 8} more</span> : null}
      </div>
      {message ? (
        <p className="mt-1 text-[0.68rem] leading-4 text-amber-900" role="status">
          {message}
        </p>
      ) : null}
    </div>
  );
}

/** Save the current place as a private point for one-click return. */
export function SavePlaceButton({
  label,
  areaSlug,
  latitude,
  longitude,
}: {
  label: string;
  areaSlug: string;
  latitude: number;
  longitude: number;
}) {
  const { isAuthenticated } = useAuth();
  const saved = useSavedLocations(isAuthenticated);
  const create = useCreateSavedLocation();
  const [message, setMessage] = useState<string | null>(null);
  const alreadySaved = Boolean(saved.data?.some((item) => item.label === label));

  if (!isAuthenticated) return null;

  function save() {
    setMessage(null);
    create.mutate(
      { label, area: areaSlug, latitude, longitude },
      {
        onError: () =>
          setMessage("Could not save this place. The label may already be used, or the point may be outside the area."),
      },
    );
  }

  return (
    <div className="text-right">
      <button
        type="button"
        onClick={save}
        disabled={alreadySaved || create.isPending}
        className="text-xs font-semibold text-ink-600 underline decoration-ink-300 underline-offset-2 hover:text-ink-900 disabled:no-underline disabled:opacity-70"
      >
        {alreadySaved ? "Saved" : create.isPending ? "Saving…" : "Save this place"}
      </button>
      {message ? (
        <p className="mt-1 max-w-[16rem] text-[0.68rem] leading-4 text-amber-900" role="status">
          {message}
        </p>
      ) : null}
    </div>
  );
}
