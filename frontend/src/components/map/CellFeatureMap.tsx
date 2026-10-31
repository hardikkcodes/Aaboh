import { Polygon, Popup } from "react-leaflet";

import type { GeoJSONGeometry } from "../../api/types";
import { formatNumber } from "../../lib/format";
import { BoundaryLayer, CivicMap, MapLegend } from "./CivicMap";
import { geometryToRings } from "./geometry";

export interface CellMapFeature {
  id: string;
  geometry: GeoJSONGeometry | null;
  value: number;
  label: string;
  unit: string;
  detail?: string;
}

export function CellFeatureMap({
  features,
  colorFor,
  legend,
  boundary,
  height = "440px",
  caption,
}: {
  features: CellMapFeature[];
  colorFor: (value: number) => string;
  legend: { label: string; color: string }[];
  boundary?: GeoJSONGeometry | null;
  height?: string;
  caption?: string;
}) {
  return (
    <div>
      <CivicMap height={height}>
        <BoundaryLayer geometry={boundary} />
        {features.map((feature) => {
          const rings = geometryToRings(feature.geometry);
          if (!rings.length) return null;
          return rings.map((ring, index) => (
            <Polygon
              key={`${feature.id}-${index}`}
              positions={ring}
              pathOptions={{
                color: "#ffffff",
                weight: 0.6,
                fillColor: colorFor(feature.value),
                fillOpacity: 0.72,
              }}
            >
              <Popup>
                <div className="max-w-[240px] text-sm">
                  <p className="font-semibold text-ink-900">{feature.label}</p>
                  <p className="mt-1 text-lg font-semibold text-ink-950">
                    {formatNumber(feature.value, 1)} {feature.unit}
                  </p>
                  {feature.detail ? (
                    <p className="mt-1 text-xs leading-5 text-ink-600">{feature.detail}</p>
                  ) : null}
                  <p className="mt-2 text-[11px] text-ink-500">
                    Aggregated analytical cell — not a point measurement.
                  </p>
                </div>
              </Popup>
            </Polygon>
          ));
        })}
      </CivicMap>
      <MapLegend items={legend} caption={caption} />
    </div>
  );
}
