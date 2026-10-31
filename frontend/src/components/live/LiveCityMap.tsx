import { useState } from "react";
import { CircleMarker, Popup } from "react-leaflet";
import { Link } from "react-router-dom";

import { useArea, useLiveMap } from "../../api/queries";
import type { LiveReportProperties } from "../../api/types";
import { LIVE_REPORT_TYPES, TRUST_META } from "../../lib/constants";
import { cn, formatRelative } from "../../lib/format";
import { useT } from "../../lib/i18n";
import { BoundaryLayer, CivicMap, MapLegend } from "../map/CivicMap";
import { ErrorState } from "../ui/Feedback";
import { ReportConfirmButtons } from "./ReportConfirmButtons";

const FALLBACK_COLOR = "#475569";

function reportColor(category: string): string {
  return LIVE_REPORT_TYPES.find((item) => item.value === category)?.color ?? FALLBACK_COLOR;
}

/** Pins fade as a report approaches expiry, so old information looks less certain. */
function remainingOpacity(report: LiveReportProperties): number {
  const start = new Date(report.occurred_at).getTime();
  const end = new Date(report.expires_at).getTime();
  const remaining = (end - Date.now()) / Math.max(end - start, 1);
  return 0.35 + 0.6 * Math.min(Math.max(remaining, 0), 1);
}

function ReportPopup({ report }: { report: LiveReportProperties }) {
  const trust = TRUST_META[report.trust];
  const details = [report.water_depth_label, report.passability_label].filter(Boolean).join(" · ");
  return (
    <div className="w-56 text-sm">
      <p className="font-semibold text-ink-900">{report.category_label}</p>
      {report.place ? <p className="text-xs text-ink-600">{report.place}</p> : null}
      {details ? <p className="mt-1 text-xs font-medium text-ink-800">{details}</p> : null}
      {report.description ? <p className="mt-1 text-xs leading-5 text-ink-700">{report.description}</p> : null}
      <p className="mt-1.5 text-xs text-ink-500">
        Reported {formatRelative(report.occurred_at)}
        {report.still_there ? ` · ${report.still_there} still there` : ""}
        {report.cleared ? ` · ${report.cleared} cleared` : ""}
      </p>
      <span className={cn("chip mt-1.5", trust.classes)}>{trust.label}</span>
      <div className="mt-2">
        <ReportConfirmButtons reportId={report.id} />
      </div>
      <Link to={`/reports/${report.id}`} className="mt-2 inline-block text-xs font-semibold underline">
        Open report
      </Link>
    </div>
  );
}

export function LiveCityMap({ height = "420px" }: { height?: string }) {
  const { t } = useT();
  const [category, setCategory] = useState("");
  const live = useLiveMap(category);
  const area = useArea();
  const features = live.data?.features ?? [];

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-1.5" role="group" aria-label="Filter reports by type">
        {[{ value: "", label: "All" }, ...LIVE_REPORT_TYPES].map((item) => (
          <button
            key={item.value}
            type="button"
            aria-pressed={category === item.value}
            onClick={() => setCategory(item.value)}
            className={cn(
              "rounded-full border px-3 py-1.5 text-xs font-medium",
              category === item.value
                ? "border-ink-900 bg-ink-900 text-white"
                : "border-ink-200 bg-white text-ink-700 hover:border-ink-300",
            )}
          >
            {t(item.label)}
          </button>
        ))}
      </div>

      {live.isError ? (
        <ErrorState error={live.error} onRetry={() => void live.refetch()} />
      ) : (
        <CivicMap height={height} zoom={12}>
          <BoundaryLayer geometry={area.data?.boundary} />
          {features.map(({ geometry, properties }) => (
            <CircleMarker
              key={properties.id}
              center={[geometry.coordinates[1], geometry.coordinates[0]]}
              radius={9}
              pathOptions={{
                color: TRUST_META[properties.trust].ring,
                weight: 2.5,
                fillColor: reportColor(properties.category),
                fillOpacity: remainingOpacity(properties),
              }}
            >
              <Popup>
                <ReportPopup report={properties} />
              </Popup>
            </CircleMarker>
          ))}
        </CivicMap>
      )}

      {live.data ? (
        <>
          <MapLegend
            items={LIVE_REPORT_TYPES.map(({ label, color }) => ({ label: t(label), color }))}
            caption="A coloured ring means confirmed. Faded pins are close to expiring."
          />
          <p className="mt-2 text-sm text-ink-700" aria-live="polite">
            {live.data.count
              ? `${live.data.count} active report(s). Latest ${formatRelative(live.data.latest_report_at)}.`
              : "No active reports here right now. That does not mean every road is clear."}
          </p>
          <p className="mt-1 text-xs leading-5 text-ink-500">{live.data.note}</p>
        </>
      ) : null}
    </div>
  );
}
