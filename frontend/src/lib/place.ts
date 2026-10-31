import type { SearchResult } from "../api/types";

/** Canonical frontend route for an area or neighbourhood status page. */
export function placePath(result: Pick<SearchResult, "type" | "slug" | "area_slug">): string {
  return result.type === "area"
    ? `/place/${result.slug}`
    : `/place/${result.area_slug}/${result.slug}`;
}
