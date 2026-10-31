import { Droplets, Leaf, MapPin, Thermometer } from "lucide-react";
import { Link } from "react-router-dom";

import type { PlaceScorecard, ReportHistory } from "../../api/types";
import { useReportHistory } from "../../api/queries";
import { SectionHeading } from "../ui/SectionHeading";

const GROUND_TEXT = { high: "Water gathers easily", medium: "In between", low: "Drains more easily" } as const;

function Score({ icon: Icon, label, value }: { icon: typeof Leaf; label: string; value: string }) {
  return (
    <div className="panel p-4">
      <p className="flex items-center gap-1.5 text-xs font-medium text-ink-600">
        <Icon className="h-4 w-4 text-brand" aria-hidden="true" />
        {label}
      </p>
      <p className="mt-1 text-sm font-semibold text-ink-900">{value}</p>
    </div>
  );
}

export function Scorecard({ card }: { card: PlaceScorecard }) {
  return (
    <section>
      <SectionHeading eyebrow="Compared with the city" title="Neighbourhood scorecard" description={card.note} />
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        {card.hotter_than_pct !== null ? (
          <Score icon={Thermometer} label="Ground heat" value={`Hotter than ${card.hotter_than_pct}% of Kolkata`} />
        ) : null}
        {card.greener_than_pct !== null ? (
          <Score icon={Leaf} label="Greenery" value={`Greener than ${card.greener_than_pct}% of Kolkata`} />
        ) : null}
        <Score icon={Droplets} label="Ground" value={GROUND_TEXT[card.ground_class]} />
      </div>
    </section>
  );
}

function HistoryDetail({ history }: { history: ReportHistory }) {
  return (
    <section className="panel p-5">
      <SectionHeading eyebrow="Issue history" title="What residents reported here" />
      <p className="mt-2 text-sm text-ink-700">{`${history.total} reports in the last ${history.window_days} days`}</p>
      <ul className="mt-3 flex flex-wrap gap-2">
        {Object.entries(history.by_category).map(([category, count]) => (
          <li key={category} className="chip border-ink-200 bg-ink-50 text-ink-700">
            {category}: {count}
          </li>
        ))}
      </ul>
      {history.recurring_water_spots.length ? (
        <>
          <p className="mt-4 text-sm font-semibold text-ink-900">Places that flood again and again</p>
          <ul className="mt-2 space-y-1 text-sm text-ink-700">
            {history.recurring_water_spots.slice(0, 5).map((spot) => (
              <li key={spot.slug} className="flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5 text-brand" aria-hidden="true" />
                <Link className="underline" to={`/place/kolkata/${spot.slug}`}>{spot.name}</Link>
                <span>{`on ${spot.days} different days`}</span>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}

/** Stays hidden until residents have reported something here. */
export function PlaceHistory({ area, neighbourhood }: { area: string; neighbourhood?: string }) {
  const history = useReportHistory(area, neighbourhood).data;
  return history?.total ? <HistoryDetail history={history} /> : null;
}
