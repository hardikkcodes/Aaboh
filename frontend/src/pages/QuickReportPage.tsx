import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { fieldErrors, normalizeError } from "../api/client";
import { useArea, useCreateIncident, useLiveMap } from "../api/queries";
import { useAuth } from "../auth/context";
import { ReportConfirmButtons } from "../components/live/ReportConfirmButtons";
import { LocationPicker } from "../components/map/CivicMap";
import { InlineSpinner, LoadingPanel } from "../components/ui/Feedback";
import { AREA_SLUG, LIVE_REPORT_TYPES, PASSABILITY_OPTIONS, WATER_DEPTHS } from "../lib/constants";
import { cn, formatRelative } from "../lib/format";
import { useT } from "../lib/i18n";
import { distanceMeters } from "../lib/place";
import { ROUGH_ACCURACY_M, useAccurateLocation } from "../lib/useAccurateLocation";

const DUPLICATE_RADIUS_M = 250;
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;

type Point = { latitude: number; longitude: number };

function ChoiceGroup({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: readonly { value: string; label: string }[];
  value: string;
  onChange: (value: string) => void;
}) {
  const { t } = useT();
  return (
    <fieldset>
      <legend className="label">{label}</legend>
      <div className="grid grid-cols-2 gap-2">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            aria-pressed={value === option.value}
            onClick={() => onChange(value === option.value ? "" : option.value)}
            className={cn(
              "min-h-12 rounded-xl border px-3 py-2 text-sm font-medium",
              value === option.value
                ? "border-ink-900 bg-ink-900 text-white"
                : "border-ink-200 bg-white text-ink-800",
            )}
          >
            {t(option.label)}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

export function QuickReportPage() {
  const navigate = useNavigate();
  const { t } = useT();
  const { isAuthenticated, isLoading } = useAuth();
  const area = useArea();
  const live = useLiveMap();
  const create = useCreateIncident();
  const [category, setCategory] = useState("waterlogging");
  const [point, setPoint] = useState<Point | null>(null);
  const [accuracy, setAccuracy] = useState<number | null>(null);
  const [locationMessage, setLocationMessage] = useState<string | null>(null);
  const [depth, setDepth] = useState("");
  const [passability, setPassability] = useState("");
  const [note, setNote] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);
  const placedByHand = useRef(false);

  const gps = useAccurateLocation((fix) => {
    if (!fix) setLocationMessage("Couldn't get your location. Tap the map instead.");
  });
  const { fix, locate } = gps;
  const locating = gps.status === "locating";

  useEffect(() => {
    if (isAuthenticated) locate();
  }, [isAuthenticated, locate]);

  useEffect(() => {
    // A point the resident placed by hand beats a GPS reading that arrives later.
    if (!fix || placedByHand.current) return;
    setPoint({ latitude: fix.latitude, longitude: fix.longitude });
    setAccuracy(fix.accuracy);
    setLocationMessage(null);
  }, [fix]);

  const nearby = useMemo(() => {
    if (!point) return [];
    return (live.data?.features ?? []).filter(
      ({ geometry, properties }) =>
        properties.category === category &&
        distanceMeters(point.latitude, point.longitude, geometry.coordinates[1], geometry.coordinates[0]) <=
          DUPLICATE_RADIUS_M,
    );
  }, [category, live.data, point]);

  if (isLoading) {
    return <div className="shell py-12"><LoadingPanel label="Checking your session" rows={2} /></div>;
  }

  if (!isAuthenticated) {
    return (
      <div className="shell max-w-xl py-12">
        <div className="panel p-6 text-center">
          <h1 className="display-title">Log in to report</h1>
          <p className="prose-civic mt-2">
            A free account helps keep the map reliable. Your name and email are never shown on reports.
          </p>
          <div className="mt-5 flex justify-center gap-3">
            <Link to="/login?next=/report" className="btn-primary">Log in</Link>
            <Link to="/register" className="btn-secondary">Create an account</Link>
          </div>
        </div>
      </div>
    );
  }

  function chooseCategory(value: string) {
    setCategory(value);
    setDepth("");
    setPassability("");
    setClientError(null);
  }

  function choosePhoto(file: File | null) {
    setClientError(file && file.size > MAX_IMAGE_BYTES ? "Choose a photo smaller than 5 MB." : null);
    setPhoto(file && file.size <= MAX_IMAGE_BYTES ? file : null);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setClientError(null);
    if (!point) {
      setClientError("Set the location first: use your location or tap the map.");
      return;
    }
    const payload = new FormData();
    payload.append("area", AREA_SLUG);
    payload.append("category", category);
    payload.append("occurred_at", new Date().toISOString());
    payload.append("latitude", String(point.latitude));
    payload.append("longitude", String(point.longitude));
    if (depth) payload.append("water_depth", depth);
    if (passability) payload.append("passability", passability);
    if (accuracy !== null) payload.append("location_accuracy_m", String(accuracy));
    if (note.trim()) payload.append("description", note.trim());
    if (photo) payload.append("attachments", photo);
    try {
      await create.mutateAsync(payload);
      navigate("/live", { state: { reported: true } });
    } catch {
      // The mutation state renders the API error below.
    }
  }

  const apiError = create.isError ? normalizeError(create.error) : null;
  const isWater = category === "waterlogging";

  return (
    <div className="shell max-w-xl py-6 sm:py-10">
      <h1 className="display-title">{t("Report what you see")}</h1>
      <p className="prose-civic mt-1">
        Reports appear on the public map, marked unconfirmed. Don't stop in unsafe water or traffic to report.
      </p>

      <form className="mt-5 space-y-5" onSubmit={(event) => void submit(event)} noValidate>
        <ChoiceGroup
          label={t("What is it?")}
          options={LIVE_REPORT_TYPES}
          value={category}
          onChange={(value) => chooseCategory(value || category)}
        />

        <div>
          <p className="label">{t("Where?")}</p>
          <button
            type="button"
            className="btn-secondary mb-2 w-full"
            onClick={() => {
              placedByHand.current = false;
              locate();
            }}
            disabled={locating}
          >
            {t(locating ? "Finding your location…" : point ? "Update to my location" : "Use my location")}
          </button>
          {locationMessage ? (
            <p className="mb-2 text-xs text-amber-900" role="status">{locationMessage}</p>
          ) : null}
          <LocationPicker
            latitude={point?.latitude ?? null}
            longitude={point?.longitude ?? null}
            onChange={(latitude, longitude) => {
              placedByHand.current = true;
              setLocationMessage(null);
              setAccuracy(null);
              setPoint({ latitude: Number(latitude.toFixed(5)), longitude: Number(longitude.toFixed(5)) });
            }}
            boundary={area.data?.boundary}
            height="240px"
            accuracy={accuracy}
          />
          {accuracy !== null ? (
            <p className={cn("mt-1 text-xs", accuracy > ROUGH_ACCURACY_M ? "font-medium text-amber-900" : "text-ink-600")} role="status">
              {accuracy > ROUGH_ACCURACY_M
                ? t("This location is rough. Tap the map to correct it.")
                : t("Accurate to about {metres} m", { metres: accuracy })}
            </p>
          ) : null}
          <p className="mt-1 text-xs text-ink-500">
            {t("The location is public. Mark the road, not a home.")}
          </p>
        </div>

        {nearby.length ? (
          <section className="rounded-xl border border-sky-200 bg-sky-50 p-3" aria-label="Reports already nearby">
            <p className="text-sm font-semibold text-sky-950">Already reported nearby</p>
            <p className="text-xs text-sky-900">Confirming helps more than a second report.</p>
            <ul className="mt-2 space-y-3">
              {nearby.slice(0, 3).map(({ properties }) => (
                <li key={properties.id}>
                  <p className="mb-1 text-xs text-sky-950">
                    {properties.place || properties.category_label} · {formatRelative(properties.occurred_at)}
                  </p>
                  <ReportConfirmButtons reportId={properties.id} />
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {isWater ? (
          <>
            <ChoiceGroup label={t("How deep?")} options={WATER_DEPTHS} value={depth} onChange={setDepth} />
            <ChoiceGroup
              label={t("What can get through?")}
              options={PASSABILITY_OPTIONS}
              value={passability}
              onChange={setPassability}
            />
          </>
        ) : null}

        <details className="rounded-xl border border-ink-100 bg-white p-3">
          <summary className="cursor-pointer text-sm font-medium text-ink-800">Add a note or photo (optional)</summary>
          <div className="mt-3 space-y-3">
            <div>
              <label className="label" htmlFor="quick-note">Note</label>
              <textarea
                id="quick-note"
                className="field min-h-20"
                maxLength={2000}
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="At least 10 characters. No names or phone numbers."
              />
            </div>
            <div>
              <label className="label" htmlFor="quick-photo">Photo</label>
              <input
                id="quick-photo"
                className="field"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(event) => choosePhoto(event.target.files?.[0] ?? null)}
              />
              <p className="mt-1 text-xs text-ink-500">Location data in the photo is removed. Avoid faces.</p>
            </div>
          </div>
        </details>

        {clientError ? (
          <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">{clientError}</p>
        ) : null}
        {apiError ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
            <p className="font-semibold">{apiError.message}</p>
            {fieldErrors(apiError.details).map((message) => <p key={message} className="mt-1 text-xs">{message}</p>)}
          </div>
        ) : null}

        <button type="submit" className="btn-primary min-h-12 w-full" disabled={create.isPending}>
          {create.isPending ? <InlineSpinner label="Sending" /> : t("Send report")}
        </button>
        <p className="text-center text-xs text-ink-500">
          {t("For immediate danger, call 112.")}{" "}
          <Link to="/reports/new" className="underline">Need the full form?</Link>
        </p>
      </form>
    </div>
  );
}
