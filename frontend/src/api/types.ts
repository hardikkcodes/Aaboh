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

export interface NearestPlace extends SearchResult {
  distance_km: number;
}

export interface NearestPlaceResponse {
  coordinate: { latitude: number; longitude: number };
  place: NearestPlace | null;
  candidates: NearestPlace[];
  note: string;
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
  provider?: string | null;
  source: SourceSummary;
  last_success_at: string | null;
  last_attempt_at?: string | null;
  count: number;
  results: Alert[];
  scope_terms?: string[];
  feed_message?: string;
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
  nh3?: number | null;
  aqi_basis?: Record<string, unknown>;
  units?: Record<string, string>;
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

export type ReportTrust = "unconfirmed" | "resident_confirmed" | "moderator_verified";
export type ConfirmationKind = "still_there" | "cleared" | "wrong";

export interface LiveReportProperties {
  id: string;
  category: string;
  category_label: string;
  description: string;
  place: string;
  water_depth: string;
  water_depth_label: string;
  passability: string;
  passability_label: string;
  trust: ReportTrust;
  still_there: number;
  cleared: number;
  occurred_at: string;
  expires_at: string;
}

export interface LiveReportFeature {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: LiveReportProperties;
}

export interface LiveMapResponse {
  type: "FeatureCollection";
  generated_at: string;
  area: { slug: string; name: string };
  count: number;
  latest_report_at: string | null;
  features: LiveReportFeature[];
  note: string;
}

export interface Incident {
  id: string;
  category: string;
  category_label: string;
  description: string;
  occurred_at: string;
  water_depth: string;
  water_depth_label: string;
  passability: string;
  passability_label: string;
  expires_at: string | null;
  cleared_at: string | null;
  is_active: boolean;
  trust: ReportTrust;
  confirmations: { still_there: number; cleared: number; wrong: number };
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
  thresholds?: Record<string, number | Record<string, number>>;
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
  preferences: {
    temperature_unit: "C" | "F";
    default_area: string | null;
    alerts_enabled?: boolean;
    quiet_hours?: boolean;
    telegram_chat_id?: string;
  };
}

export type SignalLevel = "typical" | "info" | "caution" | "warning" | "unknown";

export interface RainSoon {
  total_mm: number | null;
  max_probability_pct: number | null;
  next_rain_at: string | null;
}

export interface OutdoorWindow {
  start: string;
  end: string;
  max_heat_index_c: number;
}

export interface TodayTip {
  key: string;
  level: SignalLevel;
  params: Record<string, string | number>;
  text: string;
}

export interface TimelineHour {
  time: string;
  temperature_c: number | null;
  heat_index_c: number | null;
  rain_mm: number | null;
  rain_probability_pct: number | null;
  condition: { code: number | null; label: string };
}

export interface CommunitySpot {
  id: string;
  kind: "cool_shade" | "drinking_water" | "shelter";
  kind_label: string;
  name: string;
  latitude: number;
  longitude: number;
  is_owner: boolean;
  created_at: string;
}

export interface ReportHistory {
  window_days: number;
  total: number;
  by_category: Record<string, number>;
  by_month: Record<string, number>;
  recurring_water_spots: { name: string; slug: string; reports: number; days: number }[];
  note: string;
}

export interface ModelStatus {
  trained: {
    dataset: { rows: number; train_period: [string, string]; test_period: [string, string] };
    heat: {
      model: number;
      baseline_raw_forecast: number;
      baseline_fixed_offset: number;
      improvement_pct: number;
      promotable: boolean;
    };
    rain: {
      model: number;
      baseline_calibrated_forecast: number;
      improvement_pct: number;
      heavy_days_in_test: number;
      promotable: boolean;
    };
    limitations: string[];
  } | null;
  waiting: {
    key: string;
    name: string;
    note: string;
    progress: { label: string; value: number; target: number }[];
  }[];
}

export interface TodayResponse {
  generated_at: string;
  place: { label: string; area: string; neighbourhood: string | null };
  state: DataState;
  retrieved_at: string | null;
  season: "air" | "heat" | "monsoon" | "festive";
  rain: RainSoon;
  heat: {
    peak_heat_index_c: number | null;
    level: SignalLevel;
    night_low_c: number | null;
    note: string;
  };
  best_outdoor_window: OutdoorWindow | null;
  cleanest_air_window: { start: string; end: string; pm25: number } | null;
  timeline: TimelineHour[];
  air: { state: DataState; level: SignalLevel; aqi: number | null };
  alerts: { state: DataState; count: number; feed_message: string };
  reports: { nearby: number; city: number; radius_km: number };
  tips: TodayTip[];
  note: string;
}

export interface WeekPlanDay {
  date: string;
  rating: "good" | "fair" | "poor";
  rain_mm: number;
  max_rain_probability_pct: number;
  peak_heat_index_c: number | null;
  condition: { code: number | null; label: string };
  best_window: OutdoorWindow | null;
  hours_covered: number;
}

export interface WeekPlanResponse {
  area: { slug: string; name: string };
  generated_at: string;
  state: DataState;
  retrieved_at: string | null;
  days: WeekPlanDay[];
  note: string;
}

export interface SavedRoute {
  id: string;
  label: string;
  points: [number, number][];
  created_at: string;
}

export interface RouteReport {
  id: string;
  category_label: string;
  place: string;
  water_depth_label: string;
  passability_label: string;
  trust: ReportTrust;
  occurred_at: string;
  distance_m: number;
}

export interface RouteStatus {
  route: { id: string; label: string; points: [number, number][] };
  checked_at: string;
  summary: "serious_reports" | "reports" | "no_reports";
  buffer_m: number;
  official_alerts: number;
  rain: RainSoon;
  reports: RouteReport[];
  note: string;
}

export interface AppNotification {
  id: string;
  kind: string;
  title: string;
  body: string;
  link: string;
  read_at: string | null;
  created_at: string;
}

export interface NotificationsResponse {
  unread: number;
  results: AppNotification[];
}

export interface ImpactResponse {
  reports: number;
  reports_confirmed_by_others: number;
  confirmations_given: number;
  score: number;
  level: "new_neighbour" | "reporter" | "street_watcher" | "local_guardian";
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
    nh3?: number | null;
    aqi_basis?: Record<string, unknown>;
    units?: Record<string, string>;
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
  feed_message?: string;
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
    confidence?: "low" | "medium" | "high";
    confidence_note?: string;
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
    stale: number;
    partial: number;
    unavailable: number;
    total: number;
    confidence?: "low" | "medium" | "high";
    modules: { key: string; label: string; state: DataState; updated_at: string | null }[];
  };
  disclaimer: string;
}

