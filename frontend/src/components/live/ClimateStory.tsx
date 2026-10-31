import type { ClimateTrendsResponse } from "../../api/types";
import { formatNumber } from "../../lib/format";

/** A plain-language summary of the long-term record, using only stored values. */
export function ClimateStory({ climate }: { climate: ClimateTrendsResponse }) {
  const temperature = climate.trends.annual_temperature;
  const hotDays = climate.series.hot_days_ge_35c ?? [];
  if (!temperature || hotDays.length < 2) return null;
  const first = hotDays[0];
  const last = hotDays[hotDays.length - 1];

  return (
    <section className="panel-muted p-5">
      <p className="eyebrow">Kolkata's climate story</p>
      <p className="mt-2 font-display text-xl leading-snug text-ink-950">
        Annual temperature has changed by {temperature.slope_per_decade >= 0 ? "+" : ""}
        {formatNumber(temperature.slope_per_decade, 2)}°C per decade since {temperature.start_year}.
      </p>
      <p className="prose-civic mt-1">
        Days reaching 35°C: {first.value} in {first.year}, {last.value} in {last.year}. Single years vary, and
        these are city-scale reanalysis values, not neighbourhood measurements.
      </p>
    </section>
  );
}
