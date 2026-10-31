import type { DataState } from "../api/types";

export const AREA_SLUG = "kolkata";
export const AREA_NAME = "Kolkata";

export const NAV_ITEMS = [
  { to: "/", label: "Overview", end: true },
  { to: "/weather", label: "Weather" },
  { to: "/alerts", label: "Official alerts" },
  { to: "/heat", label: "Heat & environment" },
  { to: "/rainfall", label: "Rainfall" },
  { to: "/air-quality", label: "Air quality" },
  { to: "/climate", label: "Climate" },
  { to: "/reports", label: "Community" },
  { to: "/insights", label: "Insights" },
] as const;

/** Desktop keeps the daily-use destinations visible. */
export const PRIMARY_NAV_ITEMS = [
  { to: "/", label: "Overview", end: true },
  { to: "/weather", label: "Weather" },
  { to: "/alerts", label: "Alerts" },
  { to: "/reports", label: "Community" },
  { to: "/insights", label: "Insights" },
] as const;

/** Everything else lives behind one compact menu. */
export const SECONDARY_NAV_ITEMS = [
  { to: "/heat", label: "Heat & environment" },
  { to: "/rainfall", label: "Rainfall" },
  { to: "/air-quality", label: "Air quality" },
  { to: "/climate", label: "Climate" },
  { to: "/methodology", label: "Methodology" },
] as const;

export const INCIDENT_CATEGORIES = [
  { value: "waterlogging", label: "Waterlogging" },
  { value: "flooding", label: "Local flooding" },
  { value: "blocked_drainage", label: "Blocked drainage" },
  { value: "fallen_tree", label: "Fallen tree" },
  { value: "road_disruption", label: "Road disruption" },
  { value: "environmental_hazard", label: "Environmental hazard" },
  { value: "other", label: "Other environmental incident" },
] as const;

export const INCIDENT_STATUSES = [
  { value: "SUBMITTED", label: "Submitted" },
  { value: "UNDER_REVIEW", label: "Under review" },
  { value: "VERIFIED", label: "Verified" },
  { value: "RESOLVED", label: "Resolved" },
  { value: "REJECTED", label: "Rejected" },
  { value: "EXPIRED", label: "Expired" },
  { value: "DUPLICATE", label: "Duplicate" },
] as const;

export const MODERATOR_STATUSES = ["UNDER_REVIEW", "VERIFIED", "RESOLVED", "REJECTED", "DUPLICATE", "EXPIRED"] as const;

export const THRESHOLD_META: Record<string, { label: string; unit: string; digits: number }> = {
  hot_apparent_c: { label: "Hot apparent temperature", unit: "°C", digits: 0 },
  rain_24h_mm: { label: "24-hour rainfall", unit: "mm", digits: 1 },
  aqi_station: { label: "Station AQI", unit: "AQI", digits: 0 },
  lst_p90_c: { label: "Land-surface heat (90th percentile)", unit: "°C", digits: 0 },
  climate_anomaly_c: { label: "Temperature anomaly", unit: "°C", digits: 1 },
};

export const DATA_STATE_META: Record<
  DataState,
  { label: string; description: string; classes: string; dot: string }
> = {
  AVAILABLE: {
    label: "Available",
    description: "A recent record is available from the documented source.",
    classes: "border-emerald-200 bg-emerald-50 text-emerald-800",
    dot: "bg-emerald-500",
  },
  PARTIAL: {
    label: "Partial",
    description: "Some records or fields are available, but coverage is incomplete.",
    classes: "border-amber-200 bg-amber-50 text-amber-800",
    dot: "bg-amber-500",
  },
  STALE: {
    label: "Possibly stale",
    description: "The latest record is outside its expected refresh window.",
    classes: "border-amber-200 bg-amber-50 text-amber-800",
    dot: "bg-amber-500",
  },
  PROCESSING: {
    label: "Processing",
    description: "An ingestion or computation run is currently in progress.",
    classes: "border-sky-200 bg-sky-50 text-sky-800",
    dot: "bg-sky-500",
  },
  UNAVAILABLE: {
    label: "Unavailable",
    description: "No verified data is available. Nothing has been estimated to fill the gap.",
    classes: "border-ink-200 bg-ink-50 text-ink-700",
    dot: "bg-ink-400",
  },
};

export const MODULE_LABELS: Record<string, string> = {
  weather: "Weather forecast",
  alerts: "Official IMD alerts",
  air_quality: "CPCB air-quality stations",
  environment: "Landsat satellite layers",
  climate: "ERA5-Land climate",
  community: "Community reports",
};

export const MODULE_LINKS: Record<string, string> = {
  weather: "/weather",
  alerts: "/alerts",
  air_quality: "/air-quality",
  environment: "/heat",
  climate: "/climate",
  community: "/reports",
};

export const SEVERITY_META = {
  warning: {
    label: "Warning",
    classes: "border-red-200 bg-red-50 text-red-800",
  },
  caution: {
    label: "Caution",
    classes: "border-amber-200 bg-amber-50 text-amber-800",
  },
  info: {
    label: "Info",
    classes: "border-sky-200 bg-sky-50 text-sky-800",
  },
} as const;

export const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors';

export const KOLKATA_CENTER: [number, number] = [22.5726, 88.3639];
