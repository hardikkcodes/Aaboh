import { Briefcase, GraduationCap, Home, MapPin, X } from "lucide-react";
import { useState } from "react";

import { useCreateSavedLocation, useDeleteSavedLocation, useSavedLocations } from "../../api/queries";
import type { PickedPlace } from "../../api/types";
import { SectionHeading } from "../ui/SectionHeading";
import { PlacePicker } from "./PlacePicker";

const QUICK = [
  { label: "Home", icon: Home },
  { label: "College", icon: GraduationCap },
  { label: "Work", icon: Briefcase },
];

/** Name the places you use most, then pick them anywhere on the site. */
export function MyPlaces() {
  const saved = useSavedLocations(true).data ?? [];
  const create = useCreateSavedLocation();
  const remove = useDeleteSavedLocation();
  const [name, setName] = useState("Home");
  const [place, setPlace] = useState<PickedPlace | null>(null);
  const [failed, setFailed] = useState(false);

  async function save() {
    if (!place || !name.trim()) return;
    setFailed(false);
    try {
      await create.mutateAsync({ label: name.trim(), latitude: place.latitude, longitude: place.longitude });
      setPlace(null);
    } catch {
      setFailed(true);
    }
  }

  return (
    <section className="panel space-y-3 p-5">
      <SectionHeading title="My places" description="Save Home, College or anywhere else, then use them in routes and search." />
      {saved.length ? (
        <ul className="flex flex-wrap gap-2">
          {saved.map((item) => (
            <li key={item.id} className="chip border-ink-200 bg-white text-ink-800">
              <MapPin className="mr-1 h-3.5 w-3.5 text-brand" aria-hidden="true" />
              <span data-original-text>{item.label}</span>
              <button type="button" className="ml-1" aria-label={`Remove ${item.label}`} onClick={() => remove.mutate(item.id)}>
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      <div className="flex flex-wrap gap-2">
        {QUICK.map(({ label, icon: Icon }) => (
          <button
            key={label}
            type="button"
            aria-pressed={name === label}
            onClick={() => setName(label)}
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium ${
              name === label ? "border-ink-900 bg-ink-900 text-white" : "border-ink-200 bg-white text-ink-700"
            }`}
          >
            <Icon className="h-3.5 w-3.5" aria-hidden="true" />
            {label}
          </button>
        ))}
      </div>
      <div className="grid gap-3 sm:grid-cols-[10rem_1fr_auto] sm:items-end">
        <div>
          <label className="label" htmlFor="my-place-name">Name</label>
          <input id="my-place-name" className="field" maxLength={40} value={name} onChange={(event) => setName(event.target.value)} />
        </div>
        <PlacePicker label="Where is it?" value={place} onPick={setPlace} />
        <button type="button" className="btn-primary" disabled={!place || create.isPending} onClick={() => void save()}>
          Save place
        </button>
      </div>
      {failed ? <p className="text-xs text-red-800" role="alert">Couldn't save this place. It may be outside your saved-place limit.</p> : null}
    </section>
  );
}
