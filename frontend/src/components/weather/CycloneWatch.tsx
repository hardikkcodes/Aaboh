import { Tornado } from "lucide-react";

import { useCyclones } from "../../api/queries";

/** Appears only while a storm is active in the Bay of Bengal or Arabian Sea. */
export function CycloneWatch() {
  const cyclones = useCyclones().data?.results ?? [];
  if (!cyclones.length) return null;
  return (
    <section className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
      <h2 className="flex items-center gap-2 font-display text-lg text-amber-950">
        <Tornado className="h-5 w-5 shrink-0" aria-hidden="true" />
        Cyclone in the region
      </h2>
      <ul className="mt-2 space-y-1 text-sm text-amber-950">
        {cyclones.map((storm) => (
          <li key={storm.event_id}>
            <span data-original-text className="font-semibold">{storm.name}</span>
            {` is about ${storm.distance_km} km from Kolkata.`}
            {storm.report_url ? (
              <>
                {" "}
                <a className="underline" href={storm.report_url} target="_blank" rel="noreferrer">See its track</a>
              </>
            ) : null}
          </li>
        ))}
      </ul>
      <p className="mt-2 text-xs text-amber-900">
        From GDACS, a UN and European Commission service. Distance alone doesn't show the risk, so follow IMD for official warnings.
      </p>
    </section>
  );
}
