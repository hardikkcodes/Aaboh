export type DataState = "AVAILABLE" | "PARTIAL" | "STALE" | "UNAVAILABLE" | "PROCESSING";

export interface SourceSummary {
  slug?: string;
  name?: string;
  provider_type?: string;
  is_official?: boolean;
  attribution?: string;
  license_name?: string;
  spatial_resolution_m?: number | null;
  dataset?: string;
}

export interface ApiErrorBody {
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
  };
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Area {
  id: string;
  slug: string;
  name: string;
  level: string;
  centroid?: GeoJSONGeometry | null;
  centroid_lat: number;
  centroid_lon: number;
  area_km2: number | null;
  boundary?: GeoJSONGeometry | null;
  neighbourhood_count?: number;
  source?: SourceSummary | null;
  source_ref?: string;
}

export interface AreaDetail extends Area {
  boundary: GeoJSONGeometry | null;
  neighbourhoods: Neighbourhood[];
  grid_versions: {
    version: string;
    cell_size_m: number;
    crs: string;
    cell_count: number;
    created_at: string;
  }[];
  metadata?: Record<string, unknown>;
}

export interface GridCell {
  id: string;
  code: string;
  version: string;
  row: number;
  col: number;
  geometry: GeoJSONGeometry;
  centroid: GeoJSONGeometry;
  centroid_lat: number;
  centroid_lon: number;
  coverage_fraction: number;
  area_km2: number;
}

export interface Neighbourhood {
  id: string;
  slug: string;
  name: string;
  area: string;
  latitude: number;
  longitude: number;
  point?: GeoJSONGeometry;
}

export interface SearchResult {
  type: "area" | "neighbourhood";
  id: string;
  name: string;
  slug: string;
  area_slug: string;
  latitude: number;
  longitude: number;
}

export type GeoJSONGeometry =
  | { type: "Point"; coordinates: number[] }
  | { type: "Polygon"; coordinates: number[][][] }
  | { type: "MultiPolygon"; coordinates: number[][][][] };

export interface WeatherCondition {
  code: number;
  label: string;
  icon?: string;
}

export interface WeatherRecord {
  id: string;
  kind: "CURRENT" | "HOURLY" | "DAILY";
  valid_time: string;
  issued_at: string | null;
  retrieved_at: string;
  temperature_c: number | null;
  temperature_max_c: number | null;
  temperature_min_c: number | null;
  apparent_temperature_c: number | null;
  apparent_temperature_max_c?: number | null;
  apparent_temperature_min_c?: number | null;
  dew_point_c?: number | null;
  rain_mm?: number | null;
  showers_mm?: number | null;
  shortwave_radiation_wm2?: number | null;
  relative_humidity: number | null;
  precipitation_mm: number | null;
  precipitation_probability: number | null;
  wind_speed_kmh: number | null;
  wind_gust_kmh: number | null;
  wind_direction_deg: number | null;
  cloud_cover: number | null;
  weather_code: number | null;
  is_day: boolean | null;
  quality_status: string;
  condition: WeatherCondition | null;
  pressure_hpa?: number | null;
  visibility_m?: number | null;
}

export interface WeatherCurrentResponse {
  area: { slug: string; name: string };
  state: DataState;
  source: SourceSummary;
  observed_at: string | null;
  retrieved_at: string | null;
  record: WeatherRecord | null;
  note: string;
}

export interface WeatherForecastResponse {
  area: { slug: string; name: string };
  state: DataState;
  source: SourceSummary;
  generated_at: string;
  retrieved_at: string | null;
  current: WeatherRecord | null;
  hourly: WeatherRecord[];
  daily: WeatherRecord[];
  note: string;
}

export interface WeatherHistoryResponse {
  area: { slug: string; name: string };
  state: DataState;
  source: SourceSummary;
  start_date: string;
  end_date: string;
  retrieved_at: string | null;
  daily: WeatherRecord[];
  note: string;
}

export interface Alert {
  id: string;
  external_id: string;
  title: string;
  description: string;
  hazard: string;
  hazard_label: string;
  severity: string;
  severity_label: string;
  certainty: string;
  urgency: string;
  status: string;
  issued_at: string;
  effective_at: string | null;
  expires_at: string | null;
  areas_text: string;
  geometry: GeoJSONGeometry | null;
  source_url: string;
  retrieved_at: string;
  quality_status: string;
  is_current: boolean;
  source: SourceSummary;
}

export interface AlertsResponse {
  state: DataState;
  source: SourceSummary;
  last_success_at: string | null;
  count: number;
  results: Alert[];
  note: string;
  reason: string | null;
}

export interface AQIMeasurement {
  id: string;
  measured_at: string;
  retrieved_at: string;
  aqi: number | null;
  aqi_category: string;
  pm25: number | null;
  pm10: number | null;
  no2: number | null;
  so2: number | null;
  co: number | null;
  o3: number | null;
  quality_status: string;
  quality_flags: string[];
}

export interface AQIStation {
  id: string;
  external_id: string;
  name: string;
  city: string;
  state: string;
  point: GeoJSONGeometry;
  latitude: number;
  longitude: number;
  is_active: boolean;
  latest_measurement: AQIMeasurement | null;
  distance_km: number | null;
  source: SourceSummary;
}

export interface AirQualityStationsResponse {
  state: DataState;
  count: number;
  source: SourceSummary;
  last_success_at: string | null;
  results: AQIStation[];
  note: string;
  reason: string | null;
}

export interface AirQualityMeasurementsResponse {
  state: DataState;
  count: number;
  results: AQIMeasurement[];
  note: string;
}

export interface EnvironmentLayer {
  key: string;
  label: string;
  unit: string;
  description: string;
  native_resolution: string;
  available: boolean;
  latest_date: string | null;
}

export interface EnvironmentLayersResponse {
  state: DataState;
  source: SourceSummary;
  last_success_at: string | null;
  latest_observation_date: string | null;
  layers: EnvironmentLayer[];
  cell_size_m: number;
  note: string;
  reason: string | null;
}

export interface EnvironmentFeature {
  type: "Feature";
  geometry: GeoJSONGeometry;
  properties: {
    cell_code: string;
    value: number;
    variable: string;
    unit: string;
    observed_on: string;
    scene_id: string;
    valid_pixel_fraction: number;
    quality_flags: string[];
  };
}

export interface EnvironmentObservationsResponse {
  type: "FeatureCollection";
  state: DataState;
  variable: string;
  count: number;
  features: EnvironmentFeature[];
  note: string;
}

export interface HeatPrediction {
  id: string;
  cell_code: string;
  geometry: GeoJSONGeometry | null;
  centroid: GeoJSONGeometry | null;
  predicted_lst_c: number;
}

export interface HeatPredictionRun {
  id: string;
  status: string;
  generated_at: string;
  valid_from: string | null;
  valid_to: string | null;
  metadata: Record<string, unknown>;
  model: {
    id: string;
    name: string;
    version: string;
    algorithm: string;
    target: string;
    metrics: Record<string, number | string>;
    is_operational: boolean;
    limitations: string;
  };
}

export interface HeatPredictionsResponse {
  area: { slug: string; name: string };
  state: DataState;
  run: HeatPredictionRun | null;
  count?: number;
  results: HeatPrediction[];
  reason?: string;
  disclaimer: string;
}

export interface HeatHotspot {
  cell_code: string;
  geometry: GeoJSONGeometry;
  centroid: GeoJSONGeometry;
  lst_c: number;
  valid_pixel_fraction: number;
  scene_id: string;
}

export interface HeatHotspotsResponse {
  area: { slug: string; name: string };
  state: DataState;
  date: string | null;
  threshold_c: number | null;
  count: number;
  results: HeatHotspot[];
  reason?: string;
  method?: string;
}

export interface ModelInfoResponse {
  state: DataState;
  active_model: {
    id: string;
    name: string;
    version: string;
    algorithm: string;
    target: string;
    metrics: Record<string, number | string>;
    trained_at: string | null;
    training_period_start: string | null;
    training_period_end: string | null;
    is_operational: boolean;
    limitations: string;
  } | null;
  versions: unknown[];
  target: string;
  note: string;
  reason: string | null;
}

export interface RainfallForecastResponse {
  area: { slug: string; name: string };
  state: DataState;
  source: SourceSummary;
  generated_at: string;
  retrieved_at: string | null;
  summary: {
    next_24h_total_mm: number;
    next_24h_max_probability_pct: number | null;
    peak_hour: string | null;
    peak_hour_mm: number | null;
  };
  hourly: WeatherRecord[];
  daily: WeatherRecord[];
  note: string;
}

export interface RainfallHistoryResponse {
  area: { slug: string; name: string };
  state: DataState;
  source: SourceSummary;
  start_date: string;
  end_date: string;
  retrieved_at: string | null;
  summary: {
    total_mm: number;
    wet_days: number;
    max_daily_mm: number | null;
  };
  monthly: { month: string; precipitation_mm: number; days: number }[];
  daily: WeatherRecord[];
  note: string;
}

export interface ClimatePoint {
  year: number;
  value: number | null;
  anomaly: number | null;
  unit: string;
  period_start: string;
  period_end: string;
  baseline_value: number | null;
}

export interface ClimateTrend {
  slope_per_decade: number;
  start_year: number;
  end_year: number;
  n_years: number;
  method: string;
  caveat: string;
}

export interface ClimateTrendsResponse {
  area: { slug: string; name: string };
  state: DataState;
  source: SourceSummary;
  dataset?: {
    name: string;
    native_resolution_m: number;
    provider_access: string;
    note: string;
  };
  series: {
    annual_temperature?: ClimatePoint[];
    annual_precipitation?: ClimatePoint[];
    hot_days_ge_35c?: ClimatePoint[];
    heavy_rain_days_ge_50mm?: ClimatePoint[];
    seasonal_temperature?: Record<string, ClimatePoint[]>;
  };
  trends: {
    annual_temperature?: ClimateTrend | null;
    annual_precipitation?: ClimateTrend | null;
    hot_days_ge_35c?: ClimateTrend | null;
    seasonal_temperature?: Record<string, ClimateTrend | null>;
  };
  baselines?: Record<string, unknown>[];
  methodology: string;
  reason?: string;
}

export interface IncidentAttachment {
  id: string;
  url: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

export interface StatusHistoryEntry {
  id: string;
  from_status: string;
  from_status_label: string;
  to_status: string;
  to_status_label: string;
  note: string;
  created_at: string;
}

export interface Incident {
  id: string;
  category: string;
  category_label: string;
  description: string;
  occurred_at: string;
  status: string;
  status_label: string;
  verification_state: "UNVERIFIED" | "VERIFIED" | string;
  latitude: number;
  longitude: number;
  point: GeoJSONGeometry;
  address_text: string;
  area: { slug: string; name: string };
  neighbourhood: { slug: string; name: string } | null;
  is_public: boolean;
  verified_at: string | null;
  resolved_at: string | null;
  attachments_count: number;
  is_owner: boolean;
  created_at: string;
  updated_at: string;
  source: SourceSummary;
  attachments?: IncidentAttachment[];
  status_history?: StatusHistoryEntry[];
  moderation_note?: string;
  potential_duplicates?: DuplicateHint[];
}

export interface DuplicateHint {
  id: string;
  category: string;
  status: string;
  distance_m: number;
  occurred_at: string;
  created_at: string;
  verification_state: string;
}

export interface IncidentSummary {
  area: { slug: string; name: string };
  window_hours: number;
  total: number;
  unverified: number;
  verified: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  note: string;
}

export interface Evidence {
  evidence_type: string;
  label: string;
  source: SourceSummary;
  observed_at: string | null;
  reference: Record<string, unknown>;
  source_url: string;
  quality_status: string;
}

export interface Insight {
  id?: string;
  rule_id: string;
  kind: string;
  title: string;
  body: string;
  severity: "info" | "caution" | "warning";
  valid_from: string | null;
  valid_until: string | null;
  evidence: Evidence[];
  caveats: string[];
  generated_at?: string;
}

export interface InsightsResponse {
  area: { slug: string; name: string };
  generated_at: string;
  ruleset_version: string;
  state: DataState;
  count: number;
  insights: Insight[];
  data_availability: { module: string; state: DataState; reason?: string | null }[];
  filters?: { rule: string | null; severity: string | null };
  thresholds?: Record<string, number>;
  methodology?: string;
  disclaimer?: string;
  persisted?: number;
  persisted_ids?: string[];
}

export interface DataStatusModule {
  state: DataState;
  source: SourceSummary | null;
  last_success_at?: string | null;
  reason: string | null;
}

export interface DataStatusResponse {
  generated_at: string;
  providers: Record<string, { configured: boolean; notes?: string }>;
  modules: Record<string, DataStatusModule>;
  sources: {
    slug: string;
    name: string;
    provider_type: string;
    is_official: boolean;
    spatial_resolution_m: number | null;
    attribution: string;
    state: DataState;
    last_success_at: string | null;
  }[];
}

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: string;
  is_moderator: boolean;
  date_joined: string;
  preferences: { temperature_unit: "C" | "F"; default_area: string | null };
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface SavedLocation {
  id: string;
  label: string;
  area: string | null;
  latitude: number;
  longitude: number;
  point: GeoJSONGeometry;
  created_at: string;
}

export type PlaceRiskLevel = "low" | "elevated" | "high" | "reports_only" | "unknown";
export type PlaceStatusLevel = "typical" | "watch" | "attention" | "unknown";
export type PlaceSignalLevel = "typical" | "info" | "caution" | "warning" | "unknown";

export interface PlaceSignalInput {
  key: string;
  label: string;
  value: number;
  unit: string;
  state: DataState;
  source: SourceSummary;
  observed_at: string | null;
  contribution: number;
  detail: string;
}

export interface PlaceWaterlogging {
  state: DataState;
  level: PlaceRiskLevel;
  label: string;
  points: number;
  max_points: number;
  method: {
    id: string;
    version: string;
    label: string;
    is_ml: boolean;
    description: string;
  };
  inputs: PlaceSignalInput[];
  drivers: string[];
  reports: {
    window_hours: number;
    radius_km: number;
    verified: number;
    unverified: number;
    total: number;
  };
  caveats: string[];
}

export interface PlaceWeather {
  state: DataState;
  record: WeatherRecord | null;
  source: SourceSummary;
  retrieved_at: string | null;
  note: string;
  reason: string | null;
}

export interface PlaceRain {
  state: DataState;
  next_24h_total_mm: number | null;
  next_24h_max_probability_pct: number | null;
  peak_hour: string | null;
  peak_hour_mm: number | null;
  source: SourceSummary;
  retrieved_at: string | null;
  note: string;
  reason: string | null;
}

export interface PlaceRecentRain {
  state: DataState;
  max_daily_mm: number | null;
  total_mm: number | null;
  window_hours: number;
  days_covered: number;
  source: SourceSummary;
  observed_at: string | null;
  note: string;
}

export interface PlaceHeat {
  state: DataState;
  air: {
    state: DataState;
    temperature_c: number | null;
    apparent_temperature_c: number | null;
    value_c: number | null;
    value_label: string | null;
    level: PlaceSignalLevel;
    observed_at: string | null;
    retrieved_at: string | null;
    source: SourceSummary;
    note: string;
    reason: string | null;
  };
  land_surface: {
    state: DataState;
    latest_date: string | null;
    nearest_cell_lst_c: number | null;
    nearest_cell_code: string | null;
    distance_km: number | null;
    city_p90_c: number | null;
    observed_count: number;
    source: SourceSummary;
    note: string;
    reason: string | null;
  };
}

export interface PlaceAirQuality {
  state: DataState;
  station: { name: string; latitude: number; longitude: number } | null;
  measurement: {
    measured_at: string;
    retrieved_at: string;
    aqi: number | null;
    aqi_category: string;
    pm25: number | null;
    pm10: number | null;
    quality_status: string;
  } | null;
  distance_km: number | null;
  level: PlaceSignalLevel;
  source: SourceSummary;
  note: string;
  reason: string | null;
}

export interface PlaceAlert {
  id: string;
  title: string;
  hazard: string;
  hazard_label: string;
  severity: string;
  severity_label: string;
  issued_at: string;
  expires_at: string | null;
  areas_text: string;
  source_url: string;
  source: SourceSummary;
  quality_status: string;
}

export interface PlaceAlerts {
  state: DataState;
  count: number;
  results: PlaceAlert[];
  source: SourceSummary;
  last_success_at: string | null;
  note: string;
  reason: string | null;
}

export interface PlaceReports {
  state: DataState;
  window_hours: number;
  radius_km: number;
  total: number;
  verified: number;
  unverified: number;
  results: Incident[];
  note: string;
  reason: string | null;
}

export interface PlaceStatusResponse {
  generated_at: string;
  method_version: string;
  place: {
    area: { slug: string; name: string; centroid_lat: number; centroid_lon: number };
    neighbourhood: {
      slug: string;
      name: string;
      latitude: number;
      longitude: number;
    } | null;
    label: string;
    resolution: "area" | "neighbourhood";
    center: { latitude: number; longitude: number };
    scope_note: string;
  };
  status: {
    level: PlaceStatusLevel;
    headline: string;
    reasons: string[];
    state: DataState;
  };
  weather: PlaceWeather;
  rain: PlaceRain;
  recent_rain: PlaceRecentRain;
  waterlogging: PlaceWaterlogging;
  heat: PlaceHeat;
  air_quality: PlaceAirQuality;
  alerts: PlaceAlerts;
  reports: PlaceReports;
  coverage: {
    available: number;
    total: number;
    modules: { key: string; label: string; state: DataState }[];
  };
  disclaimer: string;
}

