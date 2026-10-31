import { useCallback, useEffect, useRef, useState } from "react";

export interface LocationFix {
  latitude: number;
  longitude: number;
  accuracy: number;
}

export type LocationStatus = "idle" | "locating" | "ready" | "error";
export type LocationProblem = "denied" | "unavailable" | "timeout" | "unsupported" | "insecure";

/** Stop early once a fix is this good. */
const GOOD_ACCURACY_M = 25;
const MAX_WAIT_MS = 12_000;
/** Beyond this, the position is likely Wi-Fi or network based and needs correcting. */
export const ROUGH_ACCURACY_M = 100;

function problemFor(code: number): LocationProblem {
  if (code === 1) return "denied";
  if (code === 3) return "timeout";
  return "unavailable";
}

/**
 * The first GPS reading is usually the worst. This watches for several seconds and
 * keeps the most accurate fix, updating as better readings arrive.
 */
export function useAccurateLocation(onFinished?: (fix: LocationFix | null) => void) {
  const [fix, setFix] = useState<LocationFix | null>(null);
  const [status, setStatus] = useState<LocationStatus>("idle");
  const [problem, setProblem] = useState<LocationProblem | null>(null);
  const watchId = useRef<number | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const best = useRef<LocationFix | null>(null);
  const finishedCallback = useRef(onFinished);
  finishedCallback.current = onFinished;

  const stopWatching = useCallback(() => {
    if (watchId.current !== null) navigator.geolocation.clearWatch(watchId.current);
    if (timer.current !== null) clearTimeout(timer.current);
    watchId.current = null;
    timer.current = null;
  }, []);

  const finish = useCallback(
    (nextProblem: LocationProblem | null) => {
      stopWatching();
      setProblem(best.current ? null : nextProblem);
      setStatus(best.current ? "ready" : "error");
      finishedCallback.current?.(best.current);
    },
    [stopWatching],
  );

  const locate = useCallback(() => {
    if (!("geolocation" in navigator)) {
      setProblem("unsupported");
      setStatus("error");
      finishedCallback.current?.(null);
      return;
    }
    if (window.isSecureContext === false) {
      setProblem("insecure");
      setStatus("error");
      finishedCallback.current?.(null);
      return;
    }
    stopWatching();
    best.current = null;
    setFix(null);
    setProblem(null);
    setStatus("locating");
    watchId.current = navigator.geolocation.watchPosition(
      (position) => {
        const { latitude, longitude, accuracy } = position.coords;
        if (best.current && accuracy >= best.current.accuracy) return;
        best.current = {
          latitude: Number(latitude.toFixed(5)),
          longitude: Number(longitude.toFixed(5)),
          accuracy: Math.round(accuracy),
        };
        setFix(best.current);
        if (accuracy <= GOOD_ACCURACY_M) finish(null);
      },
      (error) => {
        if (error.code === 1 || !best.current) finish(problemFor(error.code));
      },
      { enableHighAccuracy: true, maximumAge: 0, timeout: MAX_WAIT_MS },
    );
    timer.current = setTimeout(() => finish("timeout"), MAX_WAIT_MS);
  }, [finish, stopWatching]);

  useEffect(() => stopWatching, [stopWatching]);

  return { fix, status, problem, locate };
}
