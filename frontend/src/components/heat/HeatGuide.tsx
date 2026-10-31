import { Clock, Droplets, Flame, MapPin, Snowflake, Sun, TreePalm } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import { useHeatGuide } from "../../api/queries";
import type { HeatGuide as Guide, PickedPlace, PlaceScorecard } from "../../api/types";
import { cn, formatTime } from "../../lib/format";
import { PlacePicker } from "../place/PlacePicker";
import { SectionHeading } from "../ui/SectionHeading";

const LEVELS = {
  comfortable: { title: "Comfortable today", body: "Normal outdoor plans are fine.", tone: "border-emerald-200 bg-emerald-50" },
  caution: { title: "Warm today", body: "Drink water and take breaks if you're working outside.", tone: "border-amber-200 bg-amber-50" },
  high: { title: "High heat today", body: "Avoid hard work outdoors around midday. Keep older people and children cool.", tone: "border-amber-200 bg-amber-50" },
  dangerous: { title: "Dangerous heat today", body: "Stay out of the sun at midday. Fainting or confusion is an emergency: call 112.", tone: "border-red-200 bg-red-50" },
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function Today({ today }: { today: NonNullable<Guide["today"]> }) {
  const level = LEVELS[today.level];
  return (
    <section className={cn("rounded-2xl border p-5", level.tone)}>
      <p className="flex items-center gap-2 text-sm font-semibold text-ink-900">
        <Flame className="h-5 w-5 text-brand" aria-hidden="true" />
        {level.title}
      </p>
      <p className="mt-2 text-5xl font-bold leading-none text-ink-950">{Math.round(today.peak_feels_c)}°C</p>
      <p className="mt-1 text-sm text-ink-700">{`Feels like, at its peak around ${formatTime(today.peak_at)}`}</p>
      <p className="mt-3 text-sm text-ink-800">{level.body}</p>
      <ul className="mt-3 space-y-1 text-sm text-ink-800">
        {today.avoid_from && today.avoid_to ? (
          <li className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-brand" aria-hidden="true" />
            {`Hottest hours: ${formatTime(today.avoid_from)} to ${formatTime(today.avoid_to)}`}
          </li>
        ) : null}
        {today.uv_peak !== null && today.uv_peak >= 6 ? (
          <li className="flex items-center gap-2">
            <Sun className="h-4 w-4 text-brand" aria-hidden="true" />
            {`Strong sun: UV ${Math.round(today.uv_peak)}. Cover up at midday.`}
          </li>
        ) : null}
      </ul>
    </section>
  );
}

function PlaceCheck() {
  const [place, setPlace] = useState<PickedPlace | null>(null);
  const [card, setCard] = useState<PlaceScorecard | null | undefined>(undefined);

  async function pick(next: PickedPlace | null) {
    setPlace(next);
    setCard(undefined);
    if (!next) return;
    const response = await api.get<{ scorecard: PlaceScorecard | null }>("/heat/place/", {
      params: { lat: next.latitude, lon: next.longitude },
    });
    setCard(response.data.scorecard);
  }

  return (
    <section className="panel p-5">
      <h2 className="section-title flex items-center gap-2">
        <MapPin className="h-5 w-5 text-brand" aria-hidden="true" />
        How does your place compare?
      </h2>
      <div className="mt-3 max-w-md">
        <PlacePicker label="Your home, college or any place" value={place} onPick={(next) => void pick(next)} />
      </div>
      {card ? (
        <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          {card.hotter_than_pct !== null ? (
            <p className="rounded-xl bg-ink-50 p-3 text-ink-800">{`Ground here is hotter than ${card.hotter_than_pct}% of Kolkata.`}</p>
          ) : null}
          {card.greener_than_pct !== null ? (
            <p className="rounded-xl bg-ink-50 p-3 text-ink-800">{`Greener than ${card.greener_than_pct}% of Kolkata.`}</p>
          ) : null}
        </div>
      ) : card === null ? (
        <p className="mt-3 text-sm text-ink-600">Satellite comparison covers Kolkata only for now.</p>
      ) : null}
    </section>
  );
}

function PlaceList({ title, icon: Icon, places }: { title: string; icon: typeof Flame; places: Guide["hottest"] }) {
  return (
    <div className="panel p-4">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-ink-900">
        <Icon className="h-4 w-4 text-brand" aria-hidden="true" />
        {title}
      </h3>
      <ol className="mt-2 space-y-1 text-sm">
        {places.map((place) => (
          <li key={place.slug} className="flex justify-between gap-2">
            <Link className="text-ink-800 hover:underline" to={`/place/kolkata/${place.slug}`}>{place.name}</Link>
            <span className="font-semibold text-ink-950">{Math.round(place.ground_c)}°C</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function YearPattern({ months }: { months: Guide["months"] }) {
  const highest = Math.max(...months.map((month) => month.ground_c));
  return (
    <div className="panel p-4">
      <h3 className="text-sm font-semibold text-ink-900">When the ground gets hottest</h3>
      <ol className="mt-3 flex h-28 items-end gap-1.5">
        {months.map((month) => (
          <li key={month.month} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
            <div
              className={cn("w-full rounded-t", month.ground_c === highest ? "bg-amber-500" : "bg-amber-300")}
              style={{ height: `${Math.max(10, (month.ground_c / highest) * 100)}%` }}
              title={`${month.ground_c}°C`}
            />
            <span className="text-[0.6rem] text-ink-500">{MONTHS[month.month - 1]}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

/** The everyday answers: is it dangerous, when, and which places are better. */
export function HeatGuide() {
  const guide = useHeatGuide().data;
  if (!guide) return null;
  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
        {guide.today ? <Today today={guide.today} /> : null}
        <section className="panel p-5">
          <h2 className="section-title">Stay cooler</h2>
          <ul className="mt-3 space-y-2 text-sm text-ink-800">
            <li className="flex gap-2"><Droplets className="mt-0.5 h-4 w-4 shrink-0 text-brand" aria-hidden="true" />Drink water before you feel thirsty.</li>
            <li className="flex gap-2"><Clock className="mt-0.5 h-4 w-4 shrink-0 text-brand" aria-hidden="true" />Plan walks and errands for early morning or evening.</li>
            <li className="flex gap-2"><TreePalm className="mt-0.5 h-4 w-4 shrink-0 text-brand" aria-hidden="true" />Choose shaded streets and parks over open concrete.</li>
          </ul>
          <Link to="/spots" className="btn-secondary mt-4 text-sm">Find cool spots near you</Link>
        </section>
      </div>
      <PlaceCheck />
      {guide.hottest.length ? (
        <section>
          <SectionHeading title="Hottest and coolest places in summer" description="Typical ground heat from March to June, from satellite images. Use this to compare places." />
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            <PlaceList title="Hottest ground" icon={Flame} places={guide.hottest} />
            {guide.coolest.length ? <PlaceList title="Coolest ground" icon={Snowflake} places={guide.coolest} /> : null}
            {guide.months.length ? <YearPattern months={guide.months} /> : null}
          </div>
        </section>
      ) : null}
    </div>
  );
}
