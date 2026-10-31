import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../../api/client";
import type { NearestPlace, NearestPlaceResponse } from "../../api/types";
import { cn } from "../../lib/format";
import { placePath } from "../../lib/place";
import { useT } from "../../lib/i18n";
import { useAccurateLocation, type LocationFix, type LocationProblem } from "../../lib/useAccurateLocation";

/** Beyond this distance a match is not treated as the resident's area. */
const MAX_COVERAGE_KM = 25;

const PROBLEM_MESSAGES: Record<LocationProblem, string> = {
  denied: "Location permission was denied. Search your area instead.",
  unavailable: "Your device could not determine a location. Search your area instead.",
  timeout: "Location lookup timed out. Search your area instead.",
  unsupported: "Location is unavailable on this device. Search your area instead.",
  insecure: "Browsers only share location on a secure (https) site. Search your area instead.",
};

export function NearMeButton({
  className,
  onPlace,
}: {
  className?: string;
  /** Receives the match instead of opening its status page. */
  onPlace?: (place: NearestPlace) => void;
}) {
  const navigate = useNavigate();
  const { t } = useT();
  const [lookingUp, setLookingUp] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const lookUp = useCallback(
    async (fix: LocationFix | null) => {
      if (!fix) return;
      setLookingUp(true);
      try {
        const response = await api.get<NearestPlaceResponse>("/locations/nearest/", {
          params: { lat: fix.latitude, lon: fix.longitude },
        });
        const nearest = response.data.place;
        if (!nearest) {
          setMessage("No covered locality was found near your location. This service covers Kolkata.");
        } else if (nearest.distance_km > MAX_COVERAGE_KM) {
          setMessage(
            `You are about ${nearest.distance_km.toFixed(0)} km from the closest covered locality ` +
              `(${nearest.name}). This service covers Kolkata only.`,
          );
        } else if (onPlace) {
          onPlace(nearest);
        } else {
          navigate(placePath(nearest), {
            state: { locatedNear: true, distanceKm: nearest.distance_km },
          });
        }
      } catch {
        setMessage("Could not look up the nearest covered locality. You can still search your area.");
      } finally {
        setLookingUp(false);
      }
    },
    [navigate, onPlace],
  );

  const { fix, status, problem, locate } = useAccurateLocation((result) => void lookUp(result));
  const busy = status === "locating" || lookingUp;

  return (
    <div className={cn("space-y-1.5", className)}>
      <button
        type="button"
        onClick={() => {
          setMessage(null);
          locate();
        }}
        disabled={busy}
        className="inline-flex items-center gap-2 rounded-full border border-ink-200 bg-white px-3.5 py-2 text-xs font-semibold text-ink-800 shadow-sm transition hover:border-ink-300 disabled:cursor-wait disabled:opacity-70"
      >
        <svg viewBox="0 0 24 24" className="h-4 w-4 text-ink-500" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <circle cx="12" cy="12" r="3.5" />
          <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
        </svg>
        {busy ? t("Finding your location…") : t("Use my location")}
      </button>
      {busy && fix ? (
        <p className="text-[0.68rem] text-ink-500" role="status">
          {t("Accurate to about {metres} m", { metres: fix.accuracy })}
        </p>
      ) : null}
      {problem || message ? (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-[0.68rem] leading-4 text-amber-900" role="status">
          {problem ? PROBLEM_MESSAGES[problem] : message}
        </p>
      ) : null}
    </div>
  );
}
