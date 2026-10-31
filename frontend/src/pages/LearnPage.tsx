import { useState } from "react";

import { TopicIcon } from "../components/ui/Icon";
import { PageHeader } from "../components/ui/PageHeader";
import { cn } from "../lib/format";
import { useT } from "../lib/i18n";

interface Band {
  range: string;
  meaning: string;
  tone: string;
}

const GREEN = "bg-emerald-500";
const YELLOW = "bg-yellow-400";
const ORANGE = "bg-orange-500";
const RED = "bg-red-600";
const PURPLE = "bg-purple-700";

const GUIDES: { title: string; body: string; bands?: Band[] }[] = [
  {
    title: "AQI (Air Quality Index)",
    body: "One number that sums up how polluted the air is, based on India's national scale. Lower is better.",
    bands: [
      { range: "0–50", meaning: "Good", tone: GREEN },
      { range: "51–100", meaning: "Satisfactory", tone: GREEN },
      { range: "101–200", meaning: "Moderate: sensitive people may feel it", tone: YELLOW },
      { range: "201–300", meaning: "Poor: limit long outdoor effort", tone: ORANGE },
      { range: "301–400", meaning: "Very poor: stay out of it if you can", tone: RED },
      { range: "401+", meaning: "Severe: everyone is affected", tone: PURPLE },
    ],
  },
  {
    title: "PM2.5",
    body: "Tiny particles from traffic, burning and dust, small enough to reach your lungs. Measured in micrograms per cubic metre of air.",
  },
  {
    title: "Feels-like temperature (heat index)",
    body: "Humid air stops sweat from cooling you, so 34°C in Kolkata can feel like 40°C. This number combines temperature and humidity.",
    bands: [
      { range: "Below 32°C", meaning: "Usually comfortable with care", tone: GREEN },
      { range: "32–41°C", meaning: "Take breaks and drink water", tone: ORANGE },
      { range: "41°C and above", meaning: "Dangerous for long effort outdoors", tone: RED },
    ],
  },
  {
    title: "UV index",
    body: "How strong the sun's skin-burning rays are. It can be high even on a cloudy day.",
    bands: [
      { range: "0–2", meaning: "Low", tone: GREEN },
      { range: "3–7", meaning: "Moderate to high: shade at midday", tone: YELLOW },
      { range: "8–10", meaning: "Very high: cover up", tone: RED },
      { range: "11+", meaning: "Extreme", tone: PURPLE },
    ],
  },
  {
    title: "Rain in millimetres",
    body: "1 mm of rain would be 1 mm deep if none of it drained away. What matters for waterlogging is how much falls in a short time.",
    bands: [
      { range: "Under 5 mm", meaning: "Light: a shower", tone: GREEN },
      { range: "5–20 mm", meaning: "Moderate: wet roads", tone: YELLOW },
      { range: "20–50 mm", meaning: "Heavy: low roads may flood", tone: ORANGE },
      { range: "50 mm and above", meaning: "Very heavy: expect waterlogging", tone: RED },
    ],
  },
  {
    title: "Chance of rain (%)",
    body: "60% does not mean rain for 60% of the day. It means rain is likely in about 6 of 10 similar situations.",
  },
  {
    title: "Land-surface temperature",
    body: "How hot the ground and rooftops are, measured by satellite. It can be far hotter than the air, and shows which places hold heat. It is not the temperature you feel.",
  },
  {
    title: "NDVI, NDBI and MNDWI",
    body: "Satellite scores for greenery (NDVI), built-up land (NDBI) and water (MNDWI). Places with more trees and water usually stay cooler.",
  },
  {
    title: "Forecast, reanalysis and reports",
    body: "A forecast is a computer's prediction. Reanalysis is a computer's reconstruction of past weather. A report comes from a resident who saw something. An official warning comes from the government. This app keeps them separate.",
  },
  {
    title: "Why is it unavailable or stale?",
    body: "Unavailable means no reliable data exists right now. Stale means the latest data is older than expected. The app shows the gap instead of guessing.",
  },
];

export function LearnPage() {
  const { t } = useT();
  const [query, setQuery] = useState("");
  const shown = GUIDES.filter((guide) => `${guide.title} ${guide.body}`.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="shell space-y-5 py-5 sm:py-8">
      <PageHeader title={t("Learn")} description="What the numbers and words in this app mean, in plain language." />
      <input
        type="search"
        className="field max-w-md"
        aria-label="Search guides"
        placeholder="Search, for example AQI"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      <div className="grid gap-3 md:grid-cols-2">
        {shown.map((guide) => (
          <article key={guide.title} className="panel p-4">
            <h2 className="section-title flex items-center gap-2"><TopicIcon text={guide.title} className="h-5 w-5" />{guide.title}</h2>
            <p className="mt-1 text-sm leading-6 text-ink-700">{guide.body}</p>
            {guide.bands ? (
              <ul className="mt-3 space-y-1.5 text-sm">
                {guide.bands.map((band) => (
                  <li key={band.range} className="flex items-start gap-2">
                    <span className={cn("mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full", band.tone)} aria-hidden="true" />
                    <span>
                      <strong className="font-semibold text-ink-900">{band.range}</strong>
                      <span className="text-ink-700"> {band.meaning}</span>
                    </span>
                  </li>
                ))}
              </ul>
            ) : null}
          </article>
        ))}
      </div>
      {shown.length ? null : <p className="text-sm text-ink-600">Nothing matches that search.</p>}
    </div>
  );
}
