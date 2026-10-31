import { Home, MapPin, Search } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

import { usePlaceSuggestions, useSavedLocations } from "../../api/queries";
import type { PickedPlace, PlaceSuggestion } from "../../api/types";
import { useAuth } from "../../auth/context";
import { newSession, resolveSuggestion } from "../../lib/placeSearch";

const DEBOUNCE_MS = 250;

/** Type a place, or pick a saved one such as Home or College. */
export function PlacePicker({
  label,
  placeholder,
  value,
  onPick,
}: {
  label: string;
  placeholder?: string;
  value?: PickedPlace | null;
  onPick: (place: PickedPlace | null) => void;
}) {
  const { isAuthenticated } = useAuth();
  const saved = useSavedLocations(isAuthenticated).data ?? [];
  const id = useId();
  const box = useRef<HTMLDivElement>(null);
  const session = useRef(newSession());
  const [term, setTerm] = useState(value?.label ?? "");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [failed, setFailed] = useState(false);
  const suggestions = usePlaceSuggestions(query, session.current);

  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(term.trim()), DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [term]);

  useEffect(() => {
    setTerm(value?.label ?? "");
  }, [value?.label]);

  useEffect(() => {
    function close(event: MouseEvent) {
      if (!box.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const matching = saved.filter((place) => place.label.toLowerCase().includes(term.trim().toLowerCase()));
  const results = suggestions.data?.results ?? [];

  async function choose(item: PlaceSuggestion) {
    setOpen(false);
    setFailed(false);
    try {
      onPick(await resolveSuggestion(item, session.current));
    } catch {
      setFailed(true);
    }
    session.current = newSession();
  }

  return (
    <div ref={box} className="relative">
      <label className="label" htmlFor={id}>{label}</label>
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" aria-hidden="true" />
        <input
          id={id}
          type="search"
          className="field !pl-9"
          autoComplete="off"
          placeholder={placeholder ?? "Type a place"}
          value={term}
          onFocus={() => setOpen(true)}
          onChange={(event) => {
            setTerm(event.target.value);
            setOpen(true);
            if (value) onPick(null);
          }}
        />
      </div>
      {failed ? <p className="mt-1 text-xs text-red-800" role="alert">Couldn't load that place. Try again.</p> : null}
      {open && (matching.length || results.length) ? (
        <ul className="absolute z-[1000] mt-1 max-h-72 w-full overflow-auto rounded-xl border border-ink-100 bg-white py-1 text-sm shadow-panel">
          {matching.slice(0, 5).map((place) => (
            <li key={place.id}>
              <button
                type="button"
                className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-ink-50"
                onClick={() => {
                  setOpen(false);
                  onPick({ label: place.label, latitude: place.latitude, longitude: place.longitude });
                }}
              >
                <Home className="h-4 w-4 shrink-0 text-brand" aria-hidden="true" />
                <span data-original-text className="font-medium text-ink-900">{place.label}</span>
              </button>
            </li>
          ))}
          {results.map((item) => (
            <li key={`${item.place_id}-${item.title}`}>
              <button
                type="button"
                className="flex w-full items-start gap-2 px-3 py-2 text-left hover:bg-ink-50"
                onClick={() => void choose(item)}
              >
                <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-ink-400" aria-hidden="true" />
                <span data-original-text>
                  <span className="block font-medium text-ink-900">{item.title}</span>
                  {item.subtitle ? <span className="block text-xs text-ink-500">{item.subtitle}</span> : null}
                </span>
              </button>
            </li>
          ))}
          {suggestions.data?.provider === "google" ? (
            <li className="px-3 py-1 text-right text-[0.65rem] text-ink-400">Powered by Google</li>
          ) : null}
        </ul>
      ) : null}
    </div>
  );
}
