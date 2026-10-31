import { HeartPulse } from "lucide-react";
import { useState } from "react";

import type { TodayResponse } from "../../api/types";
import { extraCareOn, saveExtraCare } from "../../lib/preferences";

const AIR_CONCERN_AQI = 101;
const HEAT_CONCERN_C = 32;

/** Stored only on this device, because it can hint at someone's health. */
export function ExtraCare({ today }: { today: TodayResponse }) {
  const [on, setOn] = useState(extraCareOn);
  const notes = [
    (today.air.aqi ?? 0) >= AIR_CONCERN_AQI
      ? "The air may bother sensitive people today. Keep inhalers close and shorten hard outdoor effort."
      : null,
    (today.heat.peak_heat_index_c ?? 0) >= HEAT_CONCERN_C
      ? "This heat is harder on older people, young children and anyone unwell. Keep them cool and offer water often."
      : null,
  ].filter(Boolean);

  return (
    <section className="panel p-4">
      <label className="flex cursor-pointer items-center justify-between gap-3">
        <span className="flex items-center gap-2 text-sm font-semibold text-ink-900">
          <HeartPulse className="h-4 w-4 text-brand" aria-hidden="true" />
          Extra care tips
        </span>
        <input
          type="checkbox"
          checked={on}
          onChange={(event) => {
            setOn(event.target.checked);
            saveExtraCare(event.target.checked);
          }}
        />
      </label>
      <p className="mt-1 text-xs text-ink-500">For asthma, older people and young children. Saved only on this device.</p>
      {on ? (
        <ul className="mt-2 space-y-1 text-sm text-ink-700">
          {notes.length ? notes.map((note) => <li key={note}>{note}</li>) : <li>Nothing extra to watch for today.</li>}
          <li className="text-xs text-ink-500">General advice, not medical advice.</li>
        </ul>
      ) : null}
    </section>
  );
}
