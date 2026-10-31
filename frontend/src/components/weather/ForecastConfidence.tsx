import type { ModelAgreement } from "../../api/types";
import { cn, formatDay } from "../../lib/format";

const LEVELS = {
  high: { label: "Models agree", classes: "border-emerald-200 bg-emerald-50 text-emerald-800" },
  medium: { label: "Models mostly agree", classes: "border-amber-200 bg-amber-50 text-amber-800" },
  low: { label: "Models disagree", classes: "border-red-200 bg-red-50 text-red-800" },
};

export function AgreementChip({ agreement }: { agreement: ModelAgreement | null }) {
  if (!agreement) return null;
  const level = LEVELS[agreement.level];
  return (
    <span className={cn("chip", level.classes)} title={`Rain from ${agreement.rain_low_mm} to ${agreement.rain_high_mm} mm`}>
      {level.label}
    </span>
  );
}

/** Three independent weather models, side by side, for readers who want to see the range. */
export function ForecastConfidence({ days }: { days: { date: string; agreement: ModelAgreement | null }[] }) {
  const rows = days.filter((day) => day.agreement);
  if (!rows.length) return null;
  return (
    <section className="panel p-4">
      <h2 className="section-title">How sure is the rain forecast?</h2>
      <p className="mt-1 text-sm text-ink-600">
        Three independent global weather models are compared. If they disagree, plan for either outcome.
      </p>
      <ul className="mt-3 divide-y divide-ink-100">
        {rows.map((day) => (
          <li key={day.date} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
            <span className="font-medium text-ink-900">{formatDay(day.date)}</span>
            <span className="text-ink-600">
              {day.agreement?.rain_low_mm} to {day.agreement?.rain_high_mm} mm · {day.agreement?.models_wet} of{" "}
              {day.agreement?.models} expect rain
            </span>
            <AgreementChip agreement={day.agreement} />
          </li>
        ))}
      </ul>
    </section>
  );
}
