import { useState } from "react";
import { Link } from "react-router-dom";

import {
  useArea,
  useEnvironmentLayers,
  useEnvironmentObservations,
  useHeatHotspots,
  useHeatPredictions,
} from "../api/queries";
import type { HeatPrediction } from "../api/types";
import { CellFeatureMap, type CellMapFeature } from "../components/map/CellFeatureMap";
import { DataStateNotice, StateBadge } from "../components/ui/DataState";
import { ErrorState, LoadingPanel } from "../components/ui/Feedback";
import { Explain } from "../components/ui/Explain";
import { PageHeader } from "../components/ui/PageHeader";
import { SectionHeading } from "../components/ui/SectionHeading";
import { SourcePanel } from "../components/ui/SourcePanel";
import { StatCard } from "../components/ui/StatCard";
import { formatDate, formatNumber, titleCase } from "../lib/format";

const VARIABLES = [
  { key: "lst_c", label: "Land-surface temperature", unit: "°C" },
  { key: "ndvi", label: "NDVI · vegetation", unit: "index" },
  { key: "ndbi", label: "NDBI · built-up", unit: "index" },
  { key: "mndwi", label: "MNDWI · water", unit: "index" },
] as const;

function lstColor(value: number): string {
  if (value < 28) return "#1d4ed8";
  if (value < 32) return "#0ea5e9";
  if (value < 36) return "#facc15";
  if (value < 40) return "#f97316";
  if (value < 44) return "#dc2626";
  return "#7f1d1d";
}

const LST_LEGEND = [
  { label: "< 28°C", color: "#1d4ed8" },
  { label: "28–32°C", color: "#0ea5e9" },
  { label: "32–36°C", color: "#facc15" },
  { label: "36–40°C", color: "#f97316" },
  { label: "40–44°C", color: "#dc2626" },
  { label: "≥ 44°C", color: "#7f1d1d" },
];

function variableColor(variable: string): (value: number) => string {
  if (variable === "ndvi") {
    return (value) => {
      if (value < 0) return "#d6d3d1";
      if (value < 0.2) return "#fde68a";
      if (value < 0.4) return "#86efac";
      if (value < 0.6) return "#22c55e";
      return "#166534";
    };
  }
  if (variable === "ndbi") {
    return (value) => {
      if (value < -0.2) return "#bbf7d0";
      if (value < 0) return "#fef08a";
      if (value < 0.2) return "#fdba74";
      if (value < 0.4) return "#f97316";
      return "#9a3412";
    };
  }
  if (variable === "mndwi") {
    return (value) => {
      if (value < -0.2) return "#d6d3d1";
      if (value < 0) return "#fef08a";
      if (value < 0.2) return "#7dd3fc";
      if (value < 0.4) return "#0ea5e9";
      return "#1d4ed8";
    };
  }
  return lstColor;
}

function variableLegend(variable: string): { label: string; color: string }[] {
  if (variable === "ndvi") {
    return [
      { label: "< 0", color: "#d6d3d1" },
      { label: "0–0.2", color: "#fde68a" },
      { label: "0.2–0.4", color: "#86efac" },
      { label: "0.4–0.6", color: "#22c55e" },
      { label: "≥ 0.6", color: "#166534" },
    ];
  }
  if (variable === "ndbi") {
    return [
      { label: "< −0.2", color: "#bbf7d0" },
      { label: "−0.2–0", color: "#fef08a" },
      { label: "0–0.2", color: "#fdba74" },
      { label: "0.2–0.4", color: "#f97316" },
      { label: "≥ 0.4", color: "#9a3412" },
    ];
  }
  if (variable === "mndwi") {
    return [
      { label: "< −0.2", color: "#d6d3d1" },
      { label: "−0.2–0", color: "#fef08a" },
      { label: "0–0.2", color: "#7dd3fc" },
      { label: "0.2–0.4", color: "#0ea5e9" },
      { label: "≥ 0.4", color: "#1d4ed8" },
    ];
  }
  return LST_LEGEND;
}

function predictionFeatures(predictions: HeatPrediction[]): CellMapFeature[] {
  return predictions.map((item) => ({
    id: item.id,
    geometry: item.geometry,
    value: item.predicted_lst_c,
    label: `Cell ${item.cell_code}`,
    unit: "°C",
    detail: "Model-estimated land-surface temperature",
  }));
}

export function HeatPage() {
  const [variable, setVariable] = useState("lst_c");
  const area = useArea();
  const layers = useEnvironmentLayers();
  const observations = useEnvironmentObservations(variable);
  const hotspots = useHeatHotspots();
  const predictions = useHeatPredictions();

  const activeLayer = layers.data?.layers.find((layer) => layer.key === variable);
  const features: CellMapFeature[] = (observations.data?.features ?? []).map((feature) => ({
    id: feature.properties.cell_code,
    geometry: feature.geometry,
    value: feature.properties.value,
    label: `${formatDate(feature.properties.observed_on)}`,
    unit: feature.properties.unit,
    detail: `${formatNumber(feature.properties.valid_pixel_fraction * 100, 0)}% clear view`,
  }));
  const firstFeature = features[0];
  const satelliteElsewhere = hotspots.data?.state === "UNAVAILABLE" && layers.data?.state === "AVAILABLE";

  return (
    <div className="shell space-y-6 py-5 sm:py-8">
      <PageHeader
        eyebrow="Heat & environment"
        title="How hot the ground gets"
        description="Satellite maps of hot ground and rooftops, greenery, built-up land and water. Ground heat isn't the air temperature you feel, and this isn't an official heat warning."
        aside={<StateBadge state={layers.data?.state ?? "UNAVAILABLE"} />}
      />

      <section className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Latest satellite image"
          value={layers.data?.latest_observation_date ? formatDate(layers.data.latest_observation_date) : "None"}
          detail="From the latest clear-sky pass"
        />
        <StatCard
          label="Squares mapped"
          value={observations.data?.count ? String(observations.data.count) : "—"}
          detail={observations.data ? "Each square is 1 km across" : "No squares mapped yet"}
          tone="warm"
        />
        <StatCard
          label="Hottest spots"
          value={hotspots.data?.count ? String(hotspots.data.count) : "—"}
          detail={hotspots.data?.threshold_c ? `${formatNumber(hotspots.data.threshold_c, 1)}°C or hotter: the top 10%` : "Kolkata only for now"}
          tone="warm"
        />
      </section>

      {satelliteElsewhere ? (
        <p className="panel-muted p-4 text-sm text-ink-700">
          Satellite images are loaded for Kolkata only so far, so the map and figures on this page show Kolkata, not the area you picked.
        </p>
      ) : null}

      <DataStateNotice
        state={layers.data?.state ?? "UNAVAILABLE"}
        title={layers.data?.state === "AVAILABLE" ? "Satellite observations are available" : "Satellite observation layer is unavailable"}
        reason={layers.data?.reason}
      >
        <p>
          {layers.data?.state === "AVAILABLE"
            ? "Landsat scenes are aggregated to 1 km analytical cells. Cloud cover and the 16-day revisit cycle can make the latest usable scene several days old."
            : "No satellite images have been loaded yet. No satellite values, hotspots or heat predictions have been simulated to fill this page."}
        </p>
      </DataStateNotice>

      <section>
        <SectionHeading
          eyebrow="Satellite maps"
          title="Explore the maps"
          description="Switch between ground heat, greenery, built-up land and water."
          action={observations.data ? <StateBadge state={observations.data.state} /> : null}
        />
        <div className="mt-4 flex flex-wrap gap-2">
          {VARIABLES.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => setVariable(item.key)}
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                variable === item.key
                  ? "border-ink-900 bg-ink-900 text-white"
                  : "border-ink-200 bg-white text-ink-600 hover:border-ink-300"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {observations.isError ? (
          <ErrorState className="mt-5" error={observations.error} onRetry={() => void observations.refetch()} />
        ) : observations.isLoading ? (
          <div className="mt-5"><LoadingPanel label={`Loading ${activeLayer?.label ?? "environmental"} observations`} /></div>
        ) : features.length ? (
          <div className="mt-5 grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
            <div className="panel p-4 sm:p-5">
              <CellFeatureMap
                features={features}
                colorFor={variableColor(variable)}
                legend={variableLegend(variable)}
                boundary={area.data?.boundary}
                height="440px"
                caption={`${features.length} squares from the latest image`}
              />
            </div>
            <div className="space-y-4">
              <div className="panel p-5">
                <p className="eyebrow">Layer</p>
                <p className="mt-2 font-display text-xl text-ink-950">{activeLayer?.label ?? titleCase(variable)}</p>
                <p className="prose-civic mt-2">{activeLayer?.description}</p>
                <dl className="mt-4 space-y-2 text-xs">
                  <div className="flex justify-between gap-2">
                    <dt className="text-ink-500">Unit</dt>
                    <dd className="font-medium text-ink-800">{activeLayer?.unit ?? firstFeature?.unit}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-ink-500">Sharpest detail</dt>
                    <dd className="text-right font-medium text-ink-800">{activeLayer?.native_resolution}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-ink-500">Map square</dt>
                    <dd className="font-medium text-ink-800">{layers.data?.cell_size_m ?? 1000} m</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-ink-500">Image date</dt>
                    <dd className="font-medium text-ink-800">{formatDate(activeLayer?.latest_date)}</dd>
                  </div>
                </dl>
              </div>
              <div className="panel-muted p-5">
                <p className="eyebrow">Why squares?</p>
                <p className="mt-2 text-xs leading-5 text-ink-600">
                  Each square averages many smaller satellite readings. Use them to compare places,
                  not as an exact reading for one street.
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="panel-muted mt-5 p-6">
            <p className="font-display text-xl text-ink-900">No {activeLayer?.label.toLowerCase() ?? variable} observations</p>
            <p className="prose-civic mt-2">
              No cell values exist for this variable. Switch layers or read the data-availability
              explanation above. The platform has not generated placeholder cells.
            </p>
          </div>
        )}
      </section>

      {hotspots.data?.results.length ? (
        <section>
          <SectionHeading eyebrow="Observed hotspots" title="Latest surface heat" />
          <div className="panel mt-4 overflow-hidden">
            <div className="border-b border-ink-100 p-4">
              <p className="text-xs text-ink-500">
                {hotspots.data.area.name} · {formatDate(hotspots.data.date)} · {formatNumber(hotspots.data.threshold_c, 1)}°C or hotter
              </p>
            </div>
            <ol className="divide-y divide-ink-50">
              {hotspots.data.results.slice(0, 8).map((hotspot, index) => (
                <li key={hotspot.cell_code} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                  <span className="text-ink-600">
                    <span className="mr-2 text-xs text-ink-400">{index + 1}</span>
                    Near {hotspot.place}
                  </span>
                  <span className="font-semibold text-ink-900">{formatNumber(hotspot.lst_c, 1)}°C</span>
                </li>
              ))}
            </ol>
            {hotspots.data.count > 8 ? (
              <p className="border-t border-ink-100 px-4 py-2 text-xs text-ink-400">
                {`Showing 8 of ${hotspots.data.count} squares.`}
              </p>
            ) : null}
          </div>
                  </section>
      ) : null}

      {predictions.data?.results.length ? (
        <section>
          <SectionHeading eyebrow="Estimate" title="Estimated surface heat" />
          <div className="panel mt-4 p-4 sm:p-5">
            <CellFeatureMap
              features={predictionFeatures(predictions.data.results)}
              colorFor={lstColor}
              legend={LST_LEGEND}
              boundary={area.data?.boundary}
              height="330px"
              caption={`${predictions.data.results.length} estimated cells`}
            />
            <p className="mt-3 text-xs leading-5 text-amber-800">{predictions.data.disclaimer}</p>
          </div>
        </section>
      ) : null}

      <Explain title="How to read this page">
        <p>
          Satellites measure how hot the ground and rooftops are, not the air you feel. Darker, denser
          places usually hold more heat than parks and ponds.
        </p>
        <p>
          Images come from Landsat passes on clear days, so they can be days old. These maps cover
          Kolkata for now, at 1 km detail.
        </p>
      </Explain>

      <SourcePanel
        source={layers.data?.source}
        lastSuccessAt={layers.data?.last_success_at}
        note={layers.data?.note}
        extra={
          <p className="text-xs leading-5 text-ink-500">
            Satellite source: USGS Landsat Collection 2 Level 2 via Microsoft Planetary Computer. Read the{" "}
            <Link className="link" to="/methodology">methodology</Link>. Ground temperature is not air temperature.
          </p>
        }
      />
    </div>
  );
}
