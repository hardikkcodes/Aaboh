import "leaflet/dist/leaflet.css";

import { useEffect, type ReactNode } from "react";
import { CircleMarker, MapContainer, Polygon, TileLayer, useMap, useMapEvents } from "react-leaflet";

import type { GeoJSONGeometry } from "../../api/types";
import { KOLKATA_CENTER, OSM_ATTRIBUTION } from "../../lib/constants";
import { cn } from "../../lib/format";
import { geometryToRings } from "./geometry";

export function BoundaryLayer({
  geometry,
  color = "#243733",
  fillOpacity = 0.04,
}: {
  geometry: GeoJSONGeometry | null | undefined;
  color?: string;
  fillOpacity?: number;
}) {
  const rings = geometryToRings(geometry);
  if (!rings.length) return null;
  return (
    <>
      {rings.map((ring, index) => (
        <Polygon
          key={index}
          positions={ring}
          pathOptions={{ color, weight: index === 0 ? 2 : 1, fillColor: color, fillOpacity }}
        />
      ))}
    </>
  );
}

export function CivicMap({
  children,
  center = KOLKATA_CENTER,
  zoom = 11,
  height = "420px",
  className,
  attribution = true,
}: {
  children?: ReactNode;
  center?: [number, number];
  zoom?: number;
  height?: string;
  className?: string;
  attribution?: boolean;
}) {
  return (
    <div className={cn("overflow-hidden rounded-xl border border-ink-200", className)} style={{ height }}>
      <MapContainer center={center} zoom={zoom} scrollWheelZoom={false} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution={attribution ? OSM_ATTRIBUTION : undefined}
          maxZoom={19}
        />
        {children}
      </MapContainer>
    </div>
  );
}

function ClickHandler({ onPick }: { onPick: (latitude: number, longitude: number) => void }) {
  useMapEvents({
    click(event) {
      onPick(Number(event.latlng.lat.toFixed(6)), Number(event.latlng.lng.toFixed(6)));
    },
  });
  return null;
}

function FitToBoundary({ geometry }: { geometry: GeoJSONGeometry | null | undefined }) {
  const map = useMap();
  useEffect(() => {
    const rings = geometryToRings(geometry);
    if (!rings.length) return;
    const points = rings.flat();
    if (!points.length) return;
    map.fitBounds(points, { padding: [18, 18] });
  }, [geometry, map]);
  return null;
}

export function LocationPicker({
  latitude,
  longitude,
  onChange,
  boundary,
  height = "360px",
}: {
  latitude: number | null;
  longitude: number | null;
  onChange: (latitude: number, longitude: number) => void;
  boundary?: GeoJSONGeometry | null;
  height?: string;
}) {
  const hasPoint = latitude !== null && longitude !== null;
  return (
    <div>
      <CivicMap
        center={hasPoint ? [latitude as number, longitude as number] : KOLKATA_CENTER}
        zoom={hasPoint ? 14 : 11}
        height={height}
      >
        <FitToBoundary geometry={boundary} />
        <BoundaryLayer geometry={boundary} />
        <ClickHandler onPick={onChange} />
        {hasPoint ? (
          <CircleMarker
            center={[latitude as number, longitude as number]}
            radius={9}
            pathOptions={{ color: "#7c3a19", weight: 2, fillColor: "#e09a42", fillOpacity: 0.9 }}
          />
        ) : null}
      </CivicMap>
      <p className="mt-2 text-xs text-ink-500">
        {hasPoint
          ? `Selected point: ${latitude.toFixed(5)}, ${longitude.toFixed(5)}. Click the map to move it.`
          : "Click the map to place the report location. Do not use an exact home address."}
      </p>
    </div>
  );
}

export function MapLegend({ items, caption }: { items: { label: string; color: string }[]; caption?: string }) {
  return (
    <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-ink-600">
      {items.map((item) => (
        <span key={item.label} className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} aria-hidden="true" />
          {item.label}
        </span>
      ))}
      {caption ? <span className="text-ink-400">{caption}</span> : null}
    </div>
  );
}
