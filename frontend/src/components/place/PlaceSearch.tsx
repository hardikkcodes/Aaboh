import { useEffect, useId, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useLocationSearch } from "../../api/queries";
import type { SearchResult } from "../../api/types";
import { cn } from "../../lib/format";
import { placePath } from "../../lib/place";

export function PlaceSearch({ size = "sm", className }: { size?: "sm" | "lg"; className?: string }) {
  const [term, setTerm] = useState("");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const location = useLocation();
  const listId = useId();
  const { data, isFetching } = useLocationSearch(term);

  useEffect(() => {
    setOpen(false);
    setTerm("");
  }, [location.pathname]);

  useEffect(() => {
    function handleClick(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const results = data?.results.slice(0, 7) ?? [];
  const showResults = open && term.trim().length >= 2;

  function choose(result: SearchResult) {
    setOpen(false);
    setTerm("");
    navigate(placePath(result));
  }

  return (
    <div
      ref={containerRef}
      className={cn("relative", size === "lg" ? "w-full max-w-xl" : "w-full max-w-xs", className)}
    >
      <label htmlFor={listId} className="sr-only">
        Search a Kolkata area or neighbourhood
      </label>
      <input
        id={listId}
        type="search"
        value={term}
        onFocus={() => setOpen(true)}
        onChange={(event) => {
          setTerm(event.target.value);
          setOpen(true);
        }}
        onKeyDown={(event) => {
          if (event.key === "Enter" && results[0]) choose(results[0]);
        }}
        placeholder={size === "lg" ? "Search your area or neighbourhood…" : "Search an area…"}
        className={cn(
          "field",
          size === "lg"
            ? "!rounded-full !py-3.5 pl-12 pr-4 text-base shadow-panel"
            : "!rounded-full !border-ink-100 !bg-ink-50/70 !py-2 pl-9 text-xs",
        )}
        autoComplete="off"
        aria-expanded={showResults}
        aria-controls={`${listId}-results`}
      />
      <svg
        viewBox="0 0 24 24"
        className={cn(
          "pointer-events-none absolute text-ink-400",
          size === "lg" ? "left-4 top-4 h-5 w-5" : "left-3 top-2.5 h-4 w-4",
        )}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        aria-hidden="true"
      >
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-3.5-3.5" />
      </svg>
      {showResults ? (
        <div
          id={`${listId}-results`}
          className={cn(
            "absolute z-50 mt-2 w-full overflow-hidden rounded-xl border border-ink-100 bg-white shadow-panel",
            size === "lg" ? "text-sm" : "text-xs",
          )}
        >
          {results.length ? (
            <ul className="max-h-72 overflow-auto py-1">
              {results.map((result) => (
                <li key={`${result.type}-${result.id}`}>
                  <button
                    type="button"
                    className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left hover:bg-ink-50"
                    onClick={() => choose(result)}
                  >
                    <span>
                      <span className="block font-medium text-ink-900">{result.name}</span>
                      <span className="text-ink-500">
                        {result.type === "area" ? "Area" : "Neighbourhood"} · {result.area_slug}
                      </span>
                    </span>
                    <span className="text-ink-400">View status</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-3 py-3 text-ink-500">
              {isFetching ? "Searching…" : `No locality matches “${term}”.`}
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}
