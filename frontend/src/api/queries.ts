import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { currentArea } from "../lib/preferences";
import { api } from "./client";
import type {
  AirQualityMeasurementsResponse,
  AirQualityStationsResponse,
  AlertsResponse,
  Area,
  AreaDetail,
  AuthResponse,
  ClimateTrendsResponse,
  CommunitySpot,
  ConfirmationKind,
  DataStatusResponse,
  EnvironmentLayersResponse,
  EnvironmentObservationsResponse,
  HeatHotspotsResponse,
  HeatPredictionsResponse,
  ImpactResponse,
  Incident,
  IncidentSummary,
  InsightsResponse,
  LiveMapResponse,
  ModelInfoResponse,
  ModelStatus,
  NearestPlaceResponse,
  NotificationsResponse,
  Paginated,
  PlaceStatusResponse,
  RainfallForecastResponse,
  RainfallHistoryResponse,
  ReportHistory,
  RouteStatus,
  SavedLocation,
  SavedRoute,
  SearchResult,
  TodayResponse,
  User,
  WeatherCurrentResponse,
  WeatherForecastResponse,
  WeatherHistoryResponse,
  WeekPlanResponse,
  TerrainResponse,
} from "./types";


async function get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const response = await api.get<T>(url, { params });
  return response.data;
}

export const queryKeys = {
  dataStatus: ["system", "data-status"] as const,
  areas: ["locations", "areas"] as const,
  area: (slug: string) => ["locations", "area", slug] as const,
  weatherCurrent: (area: string) => ["weather", "current", area] as const,
  weatherForecast: (area: string) => ["weather", "forecast", area] as const,
  weatherHistory: (area: string, days: number) => ["weather", "history", area, days] as const,
  alerts: ["alerts"] as const,
  airStations: (area: string) => ["air-quality", "stations", area] as const,
  environmentLayers: ["environment", "layers"] as const,
  environmentObservations: (variable: string) => ["environment", "observations", variable] as const,
  heatPredictions: (area: string) => ["heat", "predictions", area] as const,
  heatHotspots: (area: string) => ["heat", "hotspots", area] as const,
  heatModel: ["heat", "model"] as const,
  rainfallForecast: (area: string) => ["rainfall", "forecast", area] as const,
  rainfallHistory: (area: string, days: number) => ["rainfall", "history", area, days] as const,
  climateTrends: (area: string) => ["climate", "trends", area] as const,
  incidents: (filters: Record<string, unknown>) => ["incidents", filters] as const,
  incident: (id: string) => ["incidents", "detail", id] as const,
  incidentSummary: (area: string) => ["incidents", "summary", area] as const,
  liveMap: (area: string, category: string) => ["incidents", "live", area, category] as const,
  insights: (area: string) => ["insights", area] as const,
  placeStatus: (area: string, neighbourhood?: string | null) =>
    ["place-status", area, neighbourhood ?? null] as const,
  search: (term: string) => ["locations", "search", term] as const,
  nearest: (latitude: number, longitude: number) =>
    ["locations", "nearest", latitude, longitude] as const,
  me: ["users", "me"] as const,
  savedLocations: ["users", "saved-locations"] as const,
};

export function useDataStatus() {
  return useQuery({
    queryKey: queryKeys.dataStatus,
    queryFn: () => get<DataStatusResponse>("/system/data-status/"),
    staleTime: 60_000,
  });
}

export function useAreas() {
  return useQuery({
    queryKey: queryKeys.areas,
    queryFn: () => get<Area[]>("/areas/"),
    staleTime: 60 * 60_000,
  });
}

export function useArea(slug = currentArea()) {
  return useQuery({
    queryKey: queryKeys.area(slug),
    queryFn: () => get<AreaDetail>(`/areas/${slug}/`),
    staleTime: 60 * 60_000,
  });
}

export function useWeatherCurrent(area = currentArea()) {
  return useQuery({
    queryKey: queryKeys.weatherCurrent(area),
    queryFn: () => get<WeatherCurrentResponse>("/weather/current/", { area }),
    staleTime: 5 * 60_000,
  });
}

export function useWeatherForecast(area = currentArea()) {
  return useQuery({
    queryKey: queryKeys.weatherForecast(area),
    queryFn: () => get<WeatherForecastResponse>("/weather/forecast/", { area, hours: 48 }),
    staleTime: 5 * 60_000,
  });
}

export function useWeatherHistory(area = currentArea(), days = 90) {
  return useQuery({
    queryKey: queryKeys.weatherHistory(area, days),
    queryFn: () =>
      get<WeatherHistoryResponse>("/weather/history/", {
        area,
        start_date: isoDaysAgo(days),
      }),
    staleTime: 30 * 60_000,
  });
}

export function useAlerts(area = currentArea()) {
  return useQuery({
    queryKey: [...queryKeys.alerts, area],
    queryFn: () => get<AlertsResponse>("/alerts/", { area }),
    staleTime: 60_000,
  });
}

export function useAirStations(area = currentArea()) {
  return useQuery({
    queryKey: queryKeys.airStations(area),
    queryFn: () => get<AirQualityStationsResponse>("/air-quality/stations/", { area }),
    staleTime: 5 * 60_000,
  });
}

export function useAirMeasurements(stationId: string | null) {
  return useQuery({
    queryKey: ["air-quality", "measurements", stationId],
    queryFn: () =>
      get<AirQualityMeasurementsResponse>("/air-quality/measurements/", {
        station: stationId,
        hours: 48,
      }),
    enabled: Boolean(stationId),
    staleTime: 5 * 60_000,
  });
}

export function useEnvironmentLayers() {
  return useQuery({
    queryKey: queryKeys.environmentLayers,
    queryFn: () => get<EnvironmentLayersResponse>("/environment/layers/"),
    staleTime: 10 * 60_000,
  });
}

export function useTerrain(area = currentArea()) {
  return useQuery({
    queryKey: ["environment", "terrain", area],
    queryFn: () => get<TerrainResponse>("/environment/terrain/", { area }),
    staleTime: 60 * 60_000,
  });
}

export function useEnvironmentObservations(variable: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.environmentObservations(variable),
    queryFn: () => get<EnvironmentObservationsResponse>("/environment/observations/", { variable }),
    enabled,
    staleTime: 10 * 60_000,
  });
}

export function useHeatPredictions(area = currentArea()) {
  return useQuery({
    queryKey: queryKeys.heatPredictions(area),
    queryFn: () => get<HeatPredictionsResponse>("/heat/predictions/", { area }),
    staleTime: 10 * 60_000,
  });
}

export function useHeatHotspots(area = currentArea()) {
  return useQuery({
    queryKey: queryKeys.heatHotspots(area),
    queryFn: () => get<HeatHotspotsResponse>("/heat/hotspots/", { area }),
    staleTime: 10 * 60_000,
  });
}

export function useHeatModel() {
  return useQuery({
    queryKey: queryKeys.heatModel,
    queryFn: () => get<ModelInfoResponse>("/heat/model-info/"),
    staleTime: 10 * 60_000,
  });
}

export function useRainfallForecast(area = currentArea()) {
  return useQuery({
    queryKey: queryKeys.rainfallForecast(area),
    queryFn: () => get<RainfallForecastResponse>("/rainfall/forecast/", { area }),
    staleTime: 5 * 60_000,
  });
}

export function useRainfallHistory(area = currentArea(), days = 365) {
  return useQuery({
    queryKey: queryKeys.rainfallHistory(area, days),
    queryFn: () => get<RainfallHistoryResponse>("/rainfall/history/", { area, days }),
    staleTime: 30 * 60_000,
  });
}

export function useClimateTrends(area = currentArea()) {
  return useQuery({
    queryKey: queryKeys.climateTrends(area),
    queryFn: () => get<ClimateTrendsResponse>("/climate/trends/", { area }),
    staleTime: 60 * 60_000,
  });
}

export interface IncidentFilters {
  area?: string;
  category?: string;
  status?: string;
  since_hours?: number;
  mine?: boolean;
}

export function useIncidents(filters: IncidentFilters = {}) {
  const params = {
    area: filters.area ?? currentArea(),
    ...(filters.category ? { category: filters.category } : {}),
    ...(filters.status ? { status: filters.status } : {}),
    ...(filters.since_hours ? { since_hours: filters.since_hours } : {}),
    ...(filters.mine ? { mine: "true" } : {}),
    page_size: 50,
  };
  return useQuery({
    queryKey: queryKeys.incidents(params),
    queryFn: () => get<Paginated<Incident>>("/incidents/", params),
    staleTime: 30_000,
  });
}

export function useIncident(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.incident(id ?? ""),
    queryFn: () => get<Incident>(`/incidents/${id}/`),
    enabled: Boolean(id),
  });
}

export function useIncidentSummary(area = currentArea()) {
  return useQuery({
    queryKey: queryKeys.incidentSummary(area),
    queryFn: () => get<IncidentSummary>("/incidents/summary/", { area }),
    staleTime: 60_000,
  });
}

export function useToday(area = currentArea(), neighbourhood?: string | null) {
  return useQuery({
    queryKey: ["today", area, neighbourhood ?? null],
    queryFn: () =>
      get<TodayResponse>("/today/", { area, ...(neighbourhood ? { neighbourhood } : {}) }),
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
  });
}

export function useModelStatus() {
  return useQuery({
    queryKey: ["system", "models"],
    queryFn: () => get<ModelStatus>("/system/models/"),
    staleTime: 5 * 60_000,
  });
}

export function useReportHistory(area = currentArea()) {
  return useQuery({
    queryKey: ["incidents", "stats", area],
    queryFn: () => get<ReportHistory>("/incidents/stats/", { area }),
    staleTime: 5 * 60_000,
  });
}

export function useSpots() {
  return useQuery({
    queryKey: ["spots"],
    queryFn: () => get<CommunitySpot[]>("/spots/"),
    staleTime: 5 * 60_000,
  });
}

export function useCreateSpot() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { kind: string; name: string; latitude: number; longitude: number }) => {
      const response = await api.post<CommunitySpot>("/spots/", payload);
      return response.data;
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["spots"] });
    },
  });
}

export function useDeleteSpot() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/spots/${id}/`);
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["spots"] });
    },
  });
}

export function useWeekPlan(area = currentArea()) {
  return useQuery({
    queryKey: ["week-plan", area],
    queryFn: () => get<WeekPlanResponse>("/planner/week/", { area }),
    staleTime: 10 * 60_000,
  });
}

export function useRoutes(enabled = true) {
  return useQuery({
    queryKey: ["users", "routes"],
    queryFn: () => get<SavedRoute[]>("/users/me/routes/"),
    enabled,
  });
}

export function useRouteStatus(id: string) {
  return useQuery({
    queryKey: ["users", "routes", id, "status"],
    queryFn: () => get<RouteStatus>(`/users/me/routes/${id}/status/`),
    staleTime: 30_000,
    refetchInterval: 2 * 60_000,
  });
}

export function useCreateRoute() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { label: string; points: [number, number][] }) => {
      const response = await api.post<SavedRoute>("/users/me/routes/", payload);
      return response.data;
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["users", "routes"] });
    },
  });
}

export function useDeleteRoute() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/users/me/routes/${id}/`);
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["users", "routes"] });
    },
  });
}

export function useNotifications(enabled = true) {
  return useQuery({
    queryKey: ["notifications"],
    queryFn: () => get<NotificationsResponse>("/notifications/"),
    enabled,
    refetchInterval: 60_000,
  });
}

export function useMarkNotificationsRead() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.post("/notifications/read/");
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

export function useImpact() {
  return useQuery({
    queryKey: ["users", "impact"],
    queryFn: () => get<ImpactResponse>("/users/me/impact/"),
  });
}

export function useLiveMap(category = "", area = currentArea()) {
  return useQuery({
    queryKey: queryKeys.liveMap(area, category),
    queryFn: () =>
      get<LiveMapResponse>("/incidents/live/", { area, ...(category ? { category } : {}) }),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useConfirmIncident() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, kind }: { id: string; kind: ConfirmationKind }) => {
      const response = await api.post<Incident>(`/incidents/${id}/confirm/`, { kind });
      return response.data;
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["incidents"] });
      void client.invalidateQueries({ queryKey: ["place-status"] });
    },
  });
}

export function useInsights(area = currentArea()) {
  return useQuery({
    queryKey: queryKeys.insights(area),
    queryFn: () => get<InsightsResponse>("/insights/", { area }),
    staleTime: 5 * 60_000,
  });
}

export function usePlaceStatus(area = currentArea(), neighbourhood?: string | null) {
  return useQuery({
    queryKey: queryKeys.placeStatus(area, neighbourhood),
    queryFn: () =>
      get<PlaceStatusResponse>(`/areas/${area}/place-status/`, {
        ...(neighbourhood ? { neighbourhood } : {}),
      }),
    staleTime: 60_000,
  });
}

export function useLocationSearch(term: string) {
  return useQuery({
    queryKey: queryKeys.search(term),
    queryFn: () => get<{ count: number; results: SearchResult[] }>("/locations/search/", { q: term }),
    staleTime: 5 * 60_000,
  });
}

/**
 * Nearest published locality to a coordinate. Straight-line matching, not
 * reverse geocoding, so the caller must never present the result as an address.
 */
export function useNearbyPlace(latitude: number | null, longitude: number | null) {
  return useQuery({
    queryKey: queryKeys.nearest(latitude ?? 0, longitude ?? 0),
    queryFn: () =>
      get<NearestPlaceResponse>("/locations/nearest/", { lat: latitude, lon: longitude }),
    enabled: latitude !== null && longitude !== null,
    staleTime: 5 * 60_000,
  });
}

export function useMe() {
  return useQuery({
    queryKey: queryKeys.me,
    queryFn: () => get<User>("/users/me/"),
    staleTime: 60_000,
  });
}

export function useSavedLocations(enabled = true) {
  return useQuery({
    queryKey: queryKeys.savedLocations,
    queryFn: () => get<SavedLocation[]>("/users/me/saved-locations/"),
    enabled,
  });
}

export function useCreateIncident() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (payload: FormData | Record<string, unknown>) => {
      const response = await api.post<Incident>("/incidents/", payload);
      return response.data;
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["incidents"] });
    },
  });
}

export function useUpdateIncident(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const response = await api.patch<Incident>(`/incidents/${id}/`, payload);
      return response.data;
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["incidents"] });
    },
  });
}

export function useModerateIncident(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const response = await api.post<Incident>(`/incidents/${id}/moderate/`, payload);
      return response.data;
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["incidents"] });
    },
  });
}

export function useUpdateMe() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { display_name?: string }) => {
      const response = await api.patch<User>("/users/me/", payload);
      return response.data;
    },
    onSuccess: (user) => {
      client.setQueryData(queryKeys.me, user);
    },
  });
}

export function useUpdatePreferences() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      temperature_unit?: "C" | "F";
      default_area?: string | null;
      alerts_enabled?: boolean;
      quiet_hours?: boolean;
      telegram_chat_id?: string;
    }) => {
      const response = await api.patch<User>("/users/me/preferences/", payload);
      return response.data;
    },
    onSuccess: (user) => {
      client.setQueryData(queryKeys.me, user);
    },
  });
}

export function useCreateSavedLocation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      label: string;
      area?: string | null;
      latitude: number;
      longitude: number;
    }) => {
      const response = await api.post<SavedLocation>("/users/me/saved-locations/", payload);
      return response.data;
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.savedLocations });
    },
  });
}

export function useDeleteSavedLocation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/users/me/saved-locations/${id}/`);
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.savedLocations });
    },
  });
}

export function useGenerateInsights() {
  const client = useQueryClient();
  return useMutation<InsightsResponse, unknown, string>({
    mutationFn: async (area) => {
      const response = await api.post<InsightsResponse>("/insights/generate/", { area });
      return response.data;
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["insights"] });
    },
  });
}

export function useLogin() {
  return useMutation({
    mutationFn: async (payload: { email: string; password: string }) => {
      const response = await api.post<AuthResponse>("/auth/login/", payload);
      return response.data;
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: async (payload: { email: string; password: string; display_name?: string }) => {
      const response = await api.post<AuthResponse>("/auth/register/", payload);
      return response.data;
    },
  });
}

export function isoDaysAgo(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString().slice(0, 10);
}
