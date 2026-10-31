import { MapPin } from "lucide-react";

import { useAreas } from "../../api/queries";
import { DEFAULT_AREA, usePreferences } from "../../lib/preferences";

/** Short names, in the order people look for them. */
const ORDER = ["kolkata", "north-kolkata", "south-kolkata", "north-24-parganas", "south-24-parganas"];

function areaLabel(slug: string, name: string): string {
  return slug === DEFAULT_AREA ? "Kolkata" : name;
}

export function AreaPicker() {
  const { area, setArea } = usePreferences();
  const areas = useAreas();
  const options = [...(areas.data ?? [])].sort((a, b) => ORDER.indexOf(a.slug) - ORDER.indexOf(b.slug));

  return (
    <label className="relative inline-flex items-center">
      <MapPin className="pointer-events-none absolute left-2.5 h-3.5 w-3.5 text-brand" aria-hidden="true" />
      <select
      aria-label="Choose your area"
      className="max-w-[10.5rem] rounded-full border border-ink-200 bg-white py-1.5 pl-7 pr-2 text-xs font-semibold text-ink-800"
      value={area}
      onChange={(event) => setArea(event.target.value)}
    >
      {options.length ? (
        options.map((item) => (
          <option key={item.slug} value={item.slug}>{areaLabel(item.slug, item.name)}</option>
        ))
      ) : (
        <option value={area}>{areaLabel(area, area)}</option>
      )}
    </select>
    </label>
  );
}
