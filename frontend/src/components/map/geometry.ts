import type { GeoJSONGeometry } from "../../api/types";

export function geometryToRings(geometry: GeoJSONGeometry | null | undefined): [number, number][][] {
  if (!geometry) return [];
  if (geometry.type === "Polygon") {
    return geometry.coordinates.map((ring) => ring.map(([lon, lat]) => [lat, lon] as [number, number]));
  }
  if (geometry.type === "MultiPolygon") {
    return geometry.coordinates.flatMap((polygon) =>
      polygon.map((ring) => ring.map(([lon, lat]) => [lat, lon] as [number, number])),
    );
  }
  return [];
}
