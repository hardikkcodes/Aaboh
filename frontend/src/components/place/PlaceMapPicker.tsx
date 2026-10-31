import { useState } from "react";
import { CircleMarker, Tooltip, useMapEvents } from "react-leaflet";
import { useNavigate } from "react-router-dom";

import { useArea, useNearbyPlace } from "../../api/queries";
import { KOLKATA_CENTER } from "../../lib/constants";
import { titleCase } from "../../lib/format";
import { placePath } from "../../lib/place";
import { BoundaryLayer, CivicMap } from "../map/CivicMap";

function PickHandler({ onPick }: { onPick: (latitude: number, longitude: number) => void }) {
  useMapEvents({
    click(event) {
      onPick(Number(event.latlng.lat.toFixed(6)), Number(event.latlng.lng.toFixed(6)));
    },
  });
  return null;
}

/**
 * Compact map picker for the area-first flow.
 *
 * Markers are published locality points. Clicking the map only looks up the
 * nearest published point: this is not reverse geocoding and does not expose a
 * street address.
 */
export function PlaceMapPicker({ areaSlug = "kolkata", height = "340px" }: { areaSlug?: string; height?: string }) {
  const area = useArea(areaSlug);
  const navigate = useNavigate();
  const [point, setPoint] = useState<{ latitude: number; longitude: number } | null>(null);
  const nearby = useNearbyPlace(point?.latitude ?? null, point?.longitude ?? null);
  const places = area.data?.neighbourhoods ?? [];
  const nearest = nearby.data?.place ?? null;
  const candidates = nearby.data?.candidates ?? [];
  const center: [number, number] = area.data
    ? [area.data.centroid_lat, area.data.centroid_lon]
    : KOLKATA_CENTER;

  return (
    <div>
      <CivicMap center={center} zoom={12} height={height}>
        <BoundaryLayer geometry={area.data?.boundary} />
        <PickHandler onPick={(latitude, longitude) => setPoint({ latitude, longitude })} />
        {places.map((place) => (
          <CircleMarker
            key={place.id}
            center={[place.latitude, place.longitude]}
            radius={6}
            pathOptions={{ color: "#ffffff", weight: 1.5, fillColor: "#243733", fillOpacity: 0.85 }}
            eventHandlers={{ click: () => navigate(`/place/${place.area}/${place.slug}`) }}
          >
            <Tooltip direction="top">{place.name}</Tooltip>
          </CircleMarker>
        ))}
        {point ? (
          <CircleMarker
            center={[point.latitude, point.longitude]}
            radius={8}
            pathOptions={{ color: "#7c3a19", weight: 2, fillColor: "#e09a42", fillOpacity: 0.9 }}
          />
        ) : null}
      </CivicMap>

      <div className="mt-3 text-xs leading-5 text-ink-600" aria-live="polite">
        {!point ? (
          <p>Click a locality dot to open its status, or click anywhere on the map to find the nearest covered locality.</p>
        ) : nearby.isFetching ? (
          <p>Looking up the nearest covered locality…</p>
        ) : nearby.isError ? (
          <p className="text-amber-900">Could not look up a nearby locality. You can still pick a locality dot.</p>
        ) : nearest ? (
          <div className="space-y-2">
            <p>
              Nearest covered locality:{" "}
              <button
                type="button"
                className="font-semibold text-ink-900 underline"
                onClick={() => navigate(placePath(nearest))}
              >
                {nearest.name}
              </button>{" "}
              · {nearest.distance_km.toFixed(1)} km away · {titleCase(nearest.type)}
            </p>
            {candidates.length > 1 ? (
              <div className="flex flex-wrap gap-1.5">
                {candidates.slice(1, 4).map((candidate) => (
                  <button
                    key={`${candidate.type}-${candidate.id}`}
                    type="button"
                    className="rounded-full border border-ink-200 bg-white px-2.5 py-1 text-[0.68rem] font-medium text-ink-700 hover:border-ink-300"
                    onClick={() => navigate(placePath(candidate))}
                  >
                    {candidate.name} · {candidate.distance_km.toFixed(1)} km
                  </button>
                ))}
              </div>
            ) : null}
            <p className="text-[0.68rem] text-ink-500">
              Matched by straight-line distance. This is not reverse geocoding and not a street address.
            </p>
          </div>
        ) : (
          <p>No covered locality was found for that point.</p>
        )}
      </div>
    </div>
  );
}
