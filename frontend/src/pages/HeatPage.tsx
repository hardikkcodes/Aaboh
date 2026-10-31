import { useState } from "react";
import { Link } from "react-router-dom";

import {
  useArea,
  useEnvironmentLayers,
  useEnvironmentObservations,
  useHeatHotspots,
  useHeatModel,
  useHeatPredictions,
} from "../api/queries";
import type { HeatPrediction } from "../api/types";
import { CellFeatureMap, type CellMapFeature } from "../components/map/CellFeatureMap";
import { DataStateNotice, StateBadge } from "../components/ui/DataState";
import { ErrorState, LoadingPanel } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";
import { SectionHeading } from "../components/ui/SectionHeading";
import { SourcePanel } from "../components/ui/SourcePanel";
import { StatCard } from "../components/ui/StatCard";
import { formatDate, formatDateTime, formatNumber, titleCase } from "../lib/format";

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
  const model = useHeatModel();

  const activeLayer = layers.data?.layers.find((layer) => layer.key === variable);
  const features: CellMapFeature[] = (observations.data?.features ?? []).map((feature) => ({
    id: feature.properties.cell_code,
    geometry: feature.geometry,
    value: feature.properties.value,
    label: `Cell ${feature.properties.cell_code}`,
    unit: feature.properties.unit,
    detail: `${formatDate(feature.properties.observed_on)} · scene ${feature.properties.scene_id} · valid pixels ${formatNumber(feature.properties.valid_pixel_fraction * 100, 0)}%`,
  }));
  const firstFeature = features[0];

  return (
    <div className="shell space-y-10 py-10 sm:py-14">
      <PageHeader
        eyebrow="Heat & environment · Landsat"
        title="Land-surface temperature, vegetation and built-up surfaces"
        description="Satellite retrievals aggregated to analytical 1 km cells. Land-surface temperature is not measured air temperature, and a hotspot map is not an official heat warning."
        aside={<StateBadge state={layers.data?.state ?? "UNAVAILABLE"} />}
      />

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Latest scene date"
          value={layers.data?.latest_observation_date ? formatDate(layers.data.latest_observation_date) : "None"}
          detail="Most recent ingested satellite observation"
        />
        <StatCard
          label="Analytical cells"
          value={observations.data?.count ? String(observations.data.count) : "—"}
          detail={observations.data ? `${formatNumber(observations.data.count, 0)} cells with ${variable.toUpperCase()} data` : "No observation features"}
          tone="warm"
        />
        <StatCard
          label="LST hotspots"
          value={hotspots.data?.count ? String(hotspots.data.count) : "—"}
          detail={hotspots.data?.threshold_c ? `At or above ${formatNumber(hotspots.data.threshold_c, 1)}°C (90th percentile)` : "No observed LST values"}
          tone="warm"
        />
        <StatCard
          label="Heat model"
          value={model.data?.active_model ? "Registered" : "Not trained"}
          detail={model.data?.active_model ? `${model.data.active_model.name} v${model.data.active_model.version}` : "No evaluated artifact has been registered"}
          tone="cool"
        />
      </section>

      <DataStateNotice
        state={layers.data?.state ?? "UNAVAILABLE"}
        title={layers.data?.state === "AVAILABLE" ? "Satellite observations are available" : "Satellite observation layer is unavailable"}
        reason={layers.data?.reason}
      >
        <p>
          {layers.data?.state === "AVAILABLE"
            ? "Landsat scenes are aggregated to 1 km analytical cells. Cloud cover and the 16-day revisit cycle can make the latest usable scene several days old."
            : "The GEE/Landsat pipeline is implemented but no credential-backed export has run. No satellite values, hotspots or heat predictions have been simulated to fill this page."}
        </p>
      </DataStateNotice>

      <section>
        <SectionHeading
          eyebrow="Satellite observations"
          title="Environmental layers"
          description="Switch layers to see the latest available date for each variable. Cell shading is an aggregation of native-resolution satellite pixels."
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
                caption={`${features.length} cells · latest common observation date`}
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
                    <dt className="text-ink-500">Native resolution</dt>
                    <dd className="text-right font-medium text-ink-800">{activeLayer?.native_resolution}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-ink-500">Analytical cell</dt>
                    <dd className="font-medium text-ink-800">{layers.data?.cell_size_m ?? 1000} m</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-ink-500">Latest layer date</dt>
                    <dd className="font-medium text-ink-800">{formatDate(activeLayer?.latest_date)}</dd>
                  </div>
                </dl>
              </div>
              <div className="panel-muted p-5">
                <p className="eyebrow">Why the grid exists</p>
                <p className="mt-2 text-xs leading-5 text-ink-600">
                  The 1 km grid is an analysis unit shared across layers. It does not turn a 30 m or
                  100 m satellite retrieval into a 1 km measurement. Values should be compared across
                  cells, not treated as point observations.
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

      <section className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
        <div>
          <SectionHeading
            eyebrow="Observed hotspots"
            title="Latest surface heat"
            action={hotspots.data ? <StateBadge state={hotspots.data.state} /> : null}
          />
          {hotspots.isLoading ? (
            <div className="mt-4"><LoadingPanel label="Loading observed hotspots" rows={2} /></div>
          ) : hotspots.data?.results.length ? (
            <div className="panel mt-4 overflow-hidden">
              <div className="border-b border-ink-100 p-4">
                <p className="text-xs text-ink-500">
                  {formatDate(hotspots.data.date)} · threshold {formatNumber(hotspots.data.threshold_c, 1)}°C
                </p>
              </div>
              <ol className="divide-y divide-ink-50">
                {hotspots.data.results.slice(0, 8).map((hotspot, index) => (
                  <li key={hotspot.cell_code} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                    <span className="text-ink-600">
                      <span className="mr-2 text-xs text-ink-400">{index + 1}</span>
                      Cell {hotspot.cell_code}
                    </span>
                    <span className="font-semibold text-ink-900">{formatNumber(hotspot.lst_c, 1)}°C</span>
                  </li>
                ))}
              </ol>
              {hotspots.data.count > 8 ? (
                <p className="border-t border-ink-100 px-4 py-2 text-xs text-ink-400">
                  Showing 8 of {hotspots.data.count} cells.
                </p>
              ) : null}
            </div>
          ) : (
            <div className="panel-muted mt-4 p-5">
              <p className="text-sm font-medium text-ink-800">No observed LST hotspots</p>
              <p className="mt-1 text-xs leading-5 text-ink-500">{hotspots.data?.reason ?? "No observation records are stored."}</p>
            </div>
          )}
          <p className="mt-3 text-xs leading-5 text-ink-500">
            {hotspots.data?.method ?? "Hotspots are described from observed land-surface temperature, not from an ML prediction."}
          </p>
        </div>

        <div>
          <SectionHeading
            eyebrow="Model estimate"
            title="Predicted surface heat"
            description="Only shown when a real evaluated model artifact and prediction run exist. Metrics are never invented."
            action={predictions.data ? <StateBadge state={predictions.data.state} /> : null}
          />
          {predictions.isLoading ? (
            <div className="mt-4"><LoadingPanel label="Loading model predictions" rows={2} /></div>
          ) : predictions.data?.results.length ? (
            <div className="mt-4 space-y-4">
              <div className="panel p-4 sm:p-5">
                <CellFeatureMap
                  features={predictionFeatures(predictions.data.results)}
                  colorFor={lstColor}
                  legend={LST_LEGEND}
                  boundary={area.data?.boundary}
                  height="330px"
                  caption={`${predictions.data.results.length} predicted cells`}
                />
              </div>
              {predictions.data.run ? (
                <div className="panel p-5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-ink-900">
                      {predictions.data.run.model.name} v{predictions.data.run.model.version}
                    </p>
                    <span className="chip border-ink-200 bg-ink-50 text-ink-700">
                      {predictions.data.run.model.algorithm}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-ink-500">
                    Generated {formatDateTime(predictions.data.run.generated_at)} · target{" "}
                    {predictions.data.run.model.target}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {Object.entries(predictions.data.run.model.metrics).map(([key, value]) => (
                      <span key={key} className="rounded-lg border border-ink-100 bg-ink-50 px-2.5 py-1.5 text-xs text-ink-700">
                        <span className="font-semibold">{key}</span>: {String(value)}
                      </span>
                    ))}
                  </div>
                  <p className="mt-3 text-xs leading-5 text-amber-800">{predictions.data.disclaimer}</p>
                </div>
              ) : null}
            </div>
          ) : (
            <div className="panel-muted mt-4 p-5">
              <p className="font-display text-xl text-ink-900">No model prediction map</p>
              <p className="prose-civic mt-2">
                {predictions.data?.reason ??
                  "The ML pipeline requires a real labelled satellite dataset and an evaluated model artifact. Until both exist, this section stays empty."}
              </p>
              <p className="mt-2 text-xs text-ink-500">{predictions.data?.disclaimer}</p>
            </div>
          )}
        </div>
      </section>

      <section>
        <SectionHeading
          eyebrow="Model registry"
          title="Heat model transparency"
          description="Metrics appear only when produced by a reproducible evaluation run. An unavailable model is shown as unavailable, not replaced by heuristics."
          action={model.data ? <StateBadge state={model.data.state} /> : null}
        />
        {model.data?.active_model ? (
          <div className="panel mt-4 grid gap-6 p-5 lg:grid-cols-[1fr_1fr] sm:p-6">
            <div>
              <p className="font-display text-2xl text-ink-950">{model.data.active_model.name}</p>
              <p className="mt-1 text-sm text-ink-500">
                Version {model.data.active_model.version} · {model.data.active_model.algorithm} ·{" "}
                {model.data.active_model.is_operational ? "Operational" : "Not operational"}
              </p>
              <p className="prose-civic mt-3">{model.data.active_model.limitations}</p>
            </div>
            <div>
              <p className="eyebrow">Evaluation metrics</p>
              {Object.keys(model.data.active_model.metrics).length ? (
                <dl className="mt-3 grid gap-2 sm:grid-cols-2">
                  {Object.entries(model.data.active_model.metrics).map(([key, value]) => (
                    <div key={key} className="rounded-xl border border-ink-100 bg-ink-50 p-3">
                      <dt className="text-[0.65rem] uppercase tracking-wide text-ink-500">{titleCase(key)}</dt>
                      <dd className="mt-1 text-sm font-semibold text-ink-900">{String(value)}</dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p className="prose-civic mt-3">No evaluation metrics were supplied with this artifact.</p>
              )}
              <p className="mt-3 text-xs text-ink-500">
                Training period: {formatDate(model.data.active_model.training_period_start)} to{" "}
                {formatDate(model.data.active_model.training_period_end)}
              </p>
            </div>
          </div>
        ) : (
          <div className="panel-muted mt-4 p-6">
            <p className="font-display text-xl text-ink-900">No evaluated heat model is registered</p>
            <p className="prose-civic mt-2">{model.data?.reason ?? "The model registry is empty."}</p>
          </div>
        )}
      </section>

      <SourcePanel
        source={layers.data?.source}
        lastSuccessAt={layers.data?.last_success_at}
        note={layers.data?.note}
        extra={
          <p className="text-xs leading-5 text-ink-500">
            Satellite source: USGS Landsat Collection 2 Level 2 via Google Earth Engine. Read the{" "}
            <Link className="link" to="/methodology">methodology</Link> and the ML pipeline contract in
            the repository documentation. LST is not air temperature.
          </p>
        }
      />
    </div>
  );
}
