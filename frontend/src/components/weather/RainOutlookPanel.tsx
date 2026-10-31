import { CloudRain, CloudSun, Umbrella, type LucideIcon } from "lucide-react";

import type { RainOutlook } from "../../api/types";
import { cn, formatDay, formatHour, formatRelative } from "../../lib/format";
import { Explain } from "../ui/Explain";

const PART_NAMES = { morning: "Morning", afternoon: "Afternoon", evening: "Evening", night: "Night" } as const;

function verdict(chance: number): { text: string; advice: string; icon: LucideIcon } {
  if (chance >= 70) return { text: "Rain is likely", advice: "Carry an umbrella.", icon: Umbrella };
  if (chance >= 40) return { text: "Rain is possible", advice: "Keep an umbrella handy.", icon: CloudRain };
  if (chance >= 15) return { text: "A small chance of rain", advice: "Probably dry, but it could shower.", icon: CloudSun };
  return { text: "Rain is unlikely", advice: "No need for an umbrella.", icon: CloudSun };
}

function ChanceBar({ chance }: { chance: number }) {
  return (
    <div className="h-2 overflow-hidden rounded-full bg-ink-100" aria-hidden="true">
      <div className="h-full rounded-full bg-sky-500 transition-all duration-500" style={{ width: `${chance}%` }} />
    </div>
  );
}

function PartTile({ name, chance }: { name: string; chance: number }) {
  return (
    <div className="rounded-xl border border-ink-100 bg-white p-3">
      <p className="text-xs text-ink-600">{name}</p>
      <p className="mt-0.5 text-xl font-semibold text-ink-950">{chance}%</p>
      <ChanceBar chance={chance} />
    </div>
  );
}

export function RainOutlookPanel({ outlook, updatedAt }: { outlook: RainOutlook; updatedAt: string | null }) {
  const today = outlook.days[0];
  const main = verdict(outlook.next_24h.chance_pct);
  const Icon = main.icon;
  const todayParts = outlook.parts.filter((part) => part.day === "today");
  const tomorrowParts = outlook.parts.filter((part) => part.day === "tomorrow");

  return (
    <div className="space-y-5">
      <section className="grid gap-5 rounded-2xl border border-sky-200 bg-sky-50 p-5 sm:p-6 lg:grid-cols-[1fr_1.2fr]">
        <div>
          <p className="flex items-center gap-2 text-sm font-semibold text-sky-900">
            <Icon className="h-5 w-5" aria-hidden="true" />
            Next 24 hours
          </p>
          <p className="mt-2 text-6xl font-bold leading-none text-ink-950">{outlook.next_24h.chance_pct}%</p>
          <p className="mt-1 text-sm text-ink-700">chance of at least 1 mm of rain</p>
          <p className="mt-3 text-lg font-semibold text-ink-950">{main.text}</p>
          <p className="text-sm text-ink-700">{main.advice}</p>
          <p className="mt-2 text-sm text-ink-700">{`Likely amount: about ${outlook.next_24h.typical_mm} mm`}</p>
        </div>
        <div className="space-y-3">
          {todayParts.length ? (
            <div>
              <p className="mb-1.5 text-sm font-semibold text-ink-900">Rest of today</p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {todayParts.map((part) => <PartTile key={part.part} name={PART_NAMES[part.part]} chance={part.chance_pct} />)}
              </div>
            </div>
          ) : null}
          <div>
            <p className="mb-1.5 text-sm font-semibold text-ink-900">Tomorrow</p>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {tomorrowParts.map((part) => <PartTile key={part.part} name={PART_NAMES[part.part]} chance={part.chance_pct} />)}
            </div>
          </div>
        </div>
      </section>

      <section className="panel p-4 sm:p-5">
        <h2 className="section-title">Hour by hour</h2>
        <ol className="-mx-1 mt-3 flex gap-2 overflow-x-auto px-1 pb-1">
          {outlook.blocks.map((block) => (
            <li key={block.start} className="w-20 shrink-0 text-center">
              <p className="text-xs text-ink-500">{formatHour(`${block.start}+05:30`)}</p>
              <div className="mx-auto mt-1 flex h-20 w-8 items-end overflow-hidden rounded-lg bg-ink-100">
                <div className="w-full rounded-lg bg-sky-500 transition-all duration-500" style={{ height: `${block.chance_pct}%` }} />
              </div>
              <p className="mt-1 text-sm font-semibold text-ink-900">{block.chance_pct}%</p>
              <p className="text-[0.68rem] text-ink-500">{block.typical_mm} mm</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="panel p-4 sm:p-5">
        <h2 className="section-title">Next 7 days</h2>
        <ul className="mt-3 divide-y divide-ink-100">
          {outlook.days.slice(0, 7).map((day) => (
            <li key={day.date} className={cn("grid grid-cols-[4.5rem_1fr_3rem] items-center gap-3 py-2.5 sm:grid-cols-[6rem_1fr_3rem_9rem]")}>
              <span className="text-sm font-medium text-ink-900">{formatDay(day.date)}</span>
              <ChanceBar chance={day.chance_pct} />
              <span className="text-right text-sm font-semibold text-ink-950">{day.chance_pct}%</span>
              <span className="col-span-3 text-xs text-ink-600 sm:col-span-1 sm:text-right">
                {`${day.low_mm} to ${day.high_mm} mm`}
                {day.heavy_chance_pct >= 5 ? <span className="ml-1 font-semibold text-red-800">{`${day.heavy_chance_pct}% heavy`}</span> : null}
              </span>
            </li>
          ))}
        </ul>
        {today && today.steady_chance_pct >= 10 ? (
          <p className="mt-2 text-sm text-ink-700">{`${today.steady_chance_pct}% chance of 10 mm or more today.`}</p>
        ) : null}
      </section>

      <Explain title="What does the percentage mean?">
        <p>{`We compare ${outlook.runs} separate runs of two global weather forecasts. The percentage is the share of runs that show rain, so 70% means 7 in 10 runs.`}</p>
        <p>It covers your wider area, not one street. A storm can miss you, or hit only you.</p>
        {updatedAt ? <p>{`Updated ${formatRelative(updatedAt)}.`}</p> : null}
      </Explain>
    </div>
  );
}
