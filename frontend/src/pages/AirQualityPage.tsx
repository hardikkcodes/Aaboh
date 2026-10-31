import { useState } from "react";
import { CircleMarker, Popup } from "react-leaflet";
import {
  CartesianGrid,
  ComposedChart,
  Line,
  Bar,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useAirMeasurements, useAirStations, useArea } from "../api/queries";
import { BoundaryLayer, CivicMap, MapLegend } from "../components/map/CivicMap";
import { DataStateNotice, StateBadge } from "../components/ui/DataState";
import { ErrorState, LoadingPanel } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";
import { SectionHeading } from "../components/ui/SectionHeading";
import { SourcePanel } from "../components/ui/SourcePanel";
import {
  formatDateTime,
  formatNumber,
  formatRelative,
  formatTime,
} from "../lib/format";

function aqiTone(category: string): string {
  const normalized = category.toLowerCase();
  if (normalized.includes("good")) return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (normalized.includes("satisfactory")) return "border-lime-200 bg-lime-50 text-lime-800";
  if (normalized.includes("moderate")) return "border-amber-200 bg-amber-50 text-amber-800";
  if (normalized.includes("poor")) return "border-orange-200 bg-orange-50 text-orange-800";
  if (normalized.includes("very poor")) return "border-red-200 bg-red-50 text-red-800";
  if (normalized.includes("severe")) return "border-red-300 bg-red-100 text-red-900";
  return "border-ink-200 bg-ink-50 text-ink-700";
}

function aqiColor(category: string): string {
  const normalized = category.toLowerCase();
  if (normalized.includes("good")) return "#059669";
  if (normalized.includes("satisfactory")) return "#65a30d";
  if (normalized.includes("moderate")) return "#d97706";
  if (normalized.includes("poor")) return "#ea580c";
  return "#dc2626";
}

export function AirQualityPage() {
  const stations = useAirStations();
  const area = useArea();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const activeStationId = selectedId ?? stations.data?.results[0]?.id ?? null;
  const measurements = useAirMeasurements(activeStationId);

  const activeStation = stations.data?.results.find((station) => station.id === activeStationId) ?? null;
  const measurementData = [...(measurements.data?.results ?? [])]
    .reverse()
    .map((item) => ({
      label: formatTime(item.measured_at),
      aqi: item.aqi,
      pm25: item.pm25,
      pm10: item.pm10,
    }));

  return (
    <div className="shell space-y-6 py-5 sm:py-8">
      <PageHeader
        eyebrow="Air quality · CPCB stations"
        title="Station observations, not a city-wide surface"
        description="Where station data exists, measurements stay attached to their station and timestamp. The platform does not interpolate a neighbourhood AQI map or fabricate readings when the CPCB feed is unavailable."
        aside={stations.data ? <StateBadge state={stations.data.state} /> : null}
      />

      {stations.isError ? (
        <ErrorState error={stations.error} onRetry={() => void stations.refetch()} />
      ) : stations.isLoading ? (
        <LoadingPanel label="Loading air-quality stations" />
      ) : (
        <>
          <DataStateNotice
            state={stations.data?.state ?? "UNAVAILABLE"}
            title={stations.data?.count ? "Station coverage is limited" : "No CPCB station measurements are available"}
            reason={stations.data?.reason}
          >
            <p>
              {stations.data?.count
                ? `${stations.data.count} active station(s) are registered. A single station reading does not describe air quality across Kolkata.`
                : "The ingestion adapter is implemented, but CPCB_API_KEY is not configured and the public data host did not respond during setup. No station rows or AQI values have been invented to fill the gap."}
            </p>
          </DataStateNotice>

          {stations.data?.results.length ? (
            <section className="grid gap-6 lg:grid-cols-[1fr_0.85fr]">
              <div>
                <SectionHeading eyebrow="Monitoring network" title="Stations near Kolkata" />
                <div className="mt-4 space-y-2">
                  {stations.data.results.map((station) => {
                    const measurement = station.latest_measurement;
                    return (
                      <button
                        key={station.id}
                        type="button"
                        onClick={() => setSelectedId(station.id)}
                        className={`w-full rounded-xl border p-4 text-left transition ${
                          station.id === activeStationId
                            ? "border-ink-400 bg-white shadow-panel"
                            : "border-ink-100 bg-white hover:border-ink-200"
                        }`}
                      >
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div>
                            <p className="text-sm font-semibold text-ink-900">{station.name}</p>
                            <p className="mt-0.5 text-xs text-ink-500">
                              {station.city}
                              {station.distance_km !== null ? ` · ${formatNumber(station.distance_km, 1)} km from area centre` : ""}
                            </p>
                          </div>
                          {measurement?.aqi !== null && measurement?.aqi !== undefined ? (
                            <span className={`chip ${aqiTone(measurement.aqi_category)}`}>
                              AQI {measurement.aqi}
                            </span>
                          ) : (
                            <span className="chip border-ink-200 bg-ink-50 text-ink-600">No recent value</span>
                          )}
                        </div>
                        {measurement ? (
                          <p className="mt-2 text-xs text-ink-500">
                            {measurement.aqi_category || "Uncategorised"} · measured {formatDateTime(measurement.measured_at)} ·{" "}
                            {formatRelative(measurement.measured_at)}
                          </p>
                        ) : (
                          <p className="mt-2 text-xs text-ink-400">No measurement in the last 7 days.</p>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <SectionHeading eyebrow="Station map" title="Locations" />
                <div className="mt-4">
                  <CivicMap height="320px">
                    <BoundaryLayer geometry={area.data?.boundary} />
                    {stations.data.results.map((station) => (
                      <CircleMarker
                        key={station.id}
                        center={[station.latitude, station.longitude]}
                        radius={station.id === activeStationId ? 10 : 7}
                        pathOptions={{
                          color: "#ffffff",
                          weight: 2,
                          fillColor: station.latest_measurement?.aqi_category
                            ? aqiColor(station.latest_measurement.aqi_category)
                            : "#94a3b8",
                          fillOpacity: 0.9,
                        }}
                      >
                        <Popup>
                          <div className="max-w-[220px] text-sm">
                            <p className="font-semibold">{station.name}</p>
                            <p className="mt-1 text-xs text-ink-600">{station.city}</p>
                            {station.latest_measurement ? (
                              <p className="mt-2 text-xs">
                                AQI {station.latest_measurement.aqi ?? "—"} ·{" "}
                                {station.latest_measurement.aqi_category || "uncategorised"}
                              </p>
                            ) : (
                              <p className="mt-2 text-xs">No recent measurement</p>
                            )}
                          </div>
                        </Popup>
                      </CircleMarker>
                    ))}
                  </CivicMap>
                  <MapLegend
                    items={[
                      { label: "Good", color: "#059669" },
                      { label: "Moderate", color: "#d97706" },
                      { label: "Poor or worse", color: "#dc2626" },
                      { label: "No recent data", color: "#94a3b8" },
                    ]}
                  />
                  <p className="mt-2 text-xs text-ink-500">
                    Station points are shown at their published coordinates. No interpolated surface is drawn.
                  </p>
                </div>
              </div>
            </section>
          ) : null}

          {activeStation ? (
            <section>
              <SectionHeading
                eyebrow="Selected station"
                title={activeStation.name}
                description={`Source: ${activeStation.source.name ?? "CPCB"} · station-level observations only.`}
                action={measurements.data ? <StateBadge state={measurements.data.state} /> : null}
              />
              {measurements.isError ? (
                <ErrorState className="mt-5" error={measurements.error} onRetry={() => void measurements.refetch()} />
              ) : measurements.isLoading ? (
                <div className="mt-5"><LoadingPanel label="Loading station measurements" /></div>
              ) : measurementData.length ? (
                <div className="panel mt-5 p-4 sm:p-6">
                  <div className="h-72 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={measurementData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                        <CartesianGrid stroke="#e3ebe8" strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="label" tick={{ fontSize: 10, fill: "#4f7d71" }} minTickGap={40} tickLine={false} axisLine={false} />
                        <YAxis yAxisId="aqi" tick={{ fontSize: 11, fill: "#4f7d71" }} tickLine={false} axisLine={false} />
                        <YAxis yAxisId="pm" orientation="right" tick={{ fontSize: 11, fill: "#6f9a8f" }} tickLine={false} axisLine={false} unit="µg/m³" />
                        <Tooltip contentStyle={{ borderRadius: 12, borderColor: "#e3ebe8", fontSize: 12 }} />
                        <Bar yAxisId="pm" dataKey="pm25" name="PM2.5 (µg/m³)" fill="#e9b76b" fillOpacity={0.7} />
                        <Bar yAxisId="pm" dataKey="pm10" name="PM10 (µg/m³)" fill="#c8d8d3" fillOpacity={0.8} />
                        <Line yAxisId="aqi" type="monotone" dataKey="aqi" name="AQI" stroke="#243733" strokeWidth={2.5} dot={false} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                  <p className="mt-3 text-xs text-ink-500">{measurements.data?.note}</p>
                </div>
              ) : (
                <div className="panel-muted mt-5 p-5">
                  <p className="text-sm font-medium text-ink-800">No measurements for this station in the selected window</p>
                  <p className="mt-1 text-xs text-ink-500">
                    A registered station is not the same as a reporting station. No values have been substituted.
                  </p>
                </div>
              )}
            </section>
          ) : null}
        </>
      )}

      <section className="grid gap-4 md:grid-cols-3">
        <div className="panel p-5">
          <p className="eyebrow">National AQI</p>
          <p className="prose-civic mt-2">
            Categories follow the source's published AQI classification. The platform stores the
            station's category rather than recalculating it from pollutants.
          </p>
        </div>
        <div className="panel p-5">
          <p className="eyebrow">No interpolation</p>
          <p className="prose-civic mt-2">
            Station values are not blended into a neighbourhood surface. Distance from the city centre
            is shown as a rough proximity indicator, not a personal exposure estimate.
          </p>
        </div>
        <div className="panel p-5">
          <p className="eyebrow">Health caution</p>
          <p className="prose-civic mt-2">
            Air-quality guidance is not medical advice. Sensitive groups should follow public-health
            guidance and consult a clinician when needed.
          </p>
        </div>
      </section>

      <SourcePanel
        source={stations.data?.source}
        lastSuccessAt={stations.data?.last_success_at}
        note={stations.data?.note}
      />
    </div>
  );
}
