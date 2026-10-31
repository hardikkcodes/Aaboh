import { Link, useLocation } from "react-router-dom";

import { usePlaceStatus, useReportHistory } from "../api/queries";
import { LiveCityMap } from "../components/live/LiveCityMap";
import { formatWithUnit } from "../lib/format";

export function LiveMapPage() {
  const location = useLocation();
  const reported = Boolean((location.state as { reported?: boolean } | null)?.reported);
  const place = usePlaceStatus();
  const rain = place.data?.rain.next_24h_total_mm;
  const repeat = useReportHistory().data?.recurring_water_spots ?? [];

  return (
    <div className="shell space-y-4 py-4 sm:py-8">
      <h1 className="font-display text-2xl text-ink-950 sm:text-3xl">Live in Kolkata</h1>

      {reported ? (
        <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900" role="status">
          Thanks. Your report is on the map, marked unconfirmed until others check it.
        </p>
      ) : null}

      <LiveCityMap height="62vh" />

      {repeat.length ? (
        <section className="panel p-4">
          <h2 className="section-title">Repeat waterlogging spots</h2>
          <p className="text-xs text-ink-500">Places residents reported on separate days in the last year.</p>
          <ul className="mt-2 space-y-1 text-sm text-ink-800">
            {repeat.map((spot) => (
              <li key={spot.slug}>
                <Link to={`/place/kolkata/${spot.slug}`} className="underline">{spot.name}</Link>: {spot.days} days, {spot.reports} reports
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <p className="text-sm leading-6 text-ink-700">
        Residents report what they see. Reports expire on their own unless someone confirms they are
        still there.{" "}
        <Link to="/report" className="font-semibold underline">Report now</Link>
      </p>

      {rain !== undefined && rain !== null ? (
        <p className="text-sm text-ink-700">
          Forecast rain, next 24 hours: <strong>{formatWithUnit(rain, "mm")}</strong>. This is a
          city-wide forecast, not a street measurement.
        </p>
      ) : null}
      <p className="text-xs leading-5 text-ink-500">
        Not an official warning or emergency service. Never walk or drive through water you can't
        judge. For immediate danger, call 112.
      </p>
    </div>
  );
}
