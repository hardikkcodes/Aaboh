import { CircleMarker, Popup } from "react-leaflet";

import type { GeoJSONGeometry, Incident } from "../../api/types";
import { titleCase, truncate } from "../../lib/format";
import { BoundaryLayer, CivicMap, MapLegend } from "./CivicMap";

function incidentColor(state: string): string {
  if (state === "VERIFIED") return "#047857";
  return "#d97706";
}

export function IncidentMap({
  incidents,
  boundary,
  height = "380px",
}: {
  incidents: Incident[];
  boundary?: GeoJSONGeometry | null;
  height?: string;
}) {
  return (
    <div>
      <CivicMap height={height}>
        <BoundaryLayer geometry={boundary} />
        {incidents.map((incident) => (
          <CircleMarker
            key={incident.id}
            center={[incident.latitude, incident.longitude]}
            radius={8}
            pathOptions={{
              color: "#ffffff",
              weight: 1.5,
              fillColor: incidentColor(incident.verification_state),
              fillOpacity: 0.9,
            }}
          >
            <Popup>
              <div className="max-w-[240px] text-sm">
                <p className="font-semibold text-ink-900">{incident.category_label}</p>
                <p className="mt-1 text-xs text-ink-600">
                  {incident.verification_state === "VERIFIED" ? "Moderator-verified" : "Unverified community report"}
                </p>
                <p className="mt-2 text-xs leading-5 text-ink-700">{truncate(incident.description, 140)}</p>
                <p className="mt-2 text-xs text-ink-500">{titleCase(incident.status)}</p>
                <a className="mt-2 inline-block text-xs font-semibold underline" href={`/reports/${incident.id}`}>
                  Open report
                </a>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </CivicMap>
      <MapLegend
        items={[
          { label: "Verified by moderator", color: "#047857" },
          { label: "Unverified community report", color: "#d97706" },
        ]}
        caption={incidents.length ? `${incidents.length} report(s) on the map` : "No reports in this view"}
      />
    </div>
  );
}
