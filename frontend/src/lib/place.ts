import type { SearchResult } from "../api/types";

/** Canonical frontend route for an area or neighbourhood status page. */
export function placePath(result: Pick<SearchResult, "type" | "slug" | "area_slug">): string {
  return result.type === "area"
    ? `/place/${result.slug}`
    : `/place/${result.area_slug}/${result.slug}`;
}

/** Straight-line distance between two coordinates. */
export function distanceMeters(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const toRadians = (degrees: number) => (degrees * Math.PI) / 180;
  const latDelta = toRadians(lat2 - lat1);
  const lonDelta = toRadians(lon2 - lon1);
  const a =
    Math.sin(latDelta / 2) ** 2 +
    Math.cos(toRadians(lat1)) * Math.cos(toRadians(lat2)) * Math.sin(lonDelta / 2) ** 2;
  return 2 * 6_371_008.8 * Math.asin(Math.sqrt(a));
}
