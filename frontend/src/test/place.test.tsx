import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import type { Incident, PlaceStatusResponse } from "../api/types";
import { AuthContext } from "../auth/context";
import { PlaceStatusPage } from "../pages/PlaceStatusPage";
import { placePath } from "../lib/place";

vi.mock("../api/queries", () => ({
  usePlaceStatus: vi.fn(),
  useLocationSearch: vi.fn(() => ({ data: { count: 0, results: [] }, isFetching: false })),
}));

import { usePlaceStatus } from "../api/queries";

const report: Incident = {
  id: "00000000-0000-0000-0000-000000000001",
  category: "waterlogging",
  category_label: "Waterlogging",
  description: "Knee-deep water across the road near the crossing.",
  occurred_at: "2026-10-31T08:00:00Z",
  status: "VERIFIED",
  status_label: "Verified",
  verification_state: "VERIFIED",
  latitude: 22.553,
  longitude: 88.352,
  point: { type: "Point", coordinates: [88.352, 22.553] },
  address_text: "",
  area: { slug: "kolkata", name: "Kolkata" },
  neighbourhood: { slug: "park-street", name: "Park Street" },
  is_public: true,
  verified_at: "2026-10-31T08:10:00Z",
  resolved_at: null,
  attachments_count: 1,
  is_owner: false,
  created_at: "2026-10-31T08:01:00Z",
  updated_at: "2026-10-31T08:10:00Z",
  source: { slug: "community_reports", name: "Community reports" },
};

const payload: PlaceStatusResponse = {
  generated_at: "2026-10-31T09:00:00Z",
  method_version: "place-status-v1",
  place: {
    area: { slug: "kolkata", name: "Kolkata", centroid_lat: 22.56, centroid_lon: 88.36 },
    neighbourhood: { slug: "park-street", name: "Park Street", latitude: 22.553, longitude: 88.352 },
    label: "Park Street, Kolkata",
    resolution: "neighbourhood",
    center: { latitude: 22.553, longitude: 88.352 },
    scope_note: "Conditions are approximated from the area forecast point and public reports.",
  },
  status: {
    level: "watch",
    headline: "Worth checking before you travel",
    reasons: ["The waterlogging risk indicator is elevated."],
    state: "PARTIAL",
  },
  weather: {
    state: "AVAILABLE",
    record: {
      id: "w1",
      kind: "CURRENT",
      valid_time: "2026-10-31T09:00:00Z",
      issued_at: null,
      retrieved_at: "2026-10-31T09:00:00Z",
      temperature_c: 31.2,
      temperature_max_c: null,
      temperature_min_c: null,
      apparent_temperature_c: 37.4,
      relative_humidity: 78,
      precipitation_mm: 0,
      precipitation_probability: 40,
      wind_speed_kmh: 12,
      wind_gust_kmh: 20,
      wind_direction_deg: 180,
      cloud_cover: 70,
      weather_code: 2,
      is_day: true,
      quality_status: "AVAILABLE",
      condition: { code: 2, label: "Partly cloudy" },
    },
    source: { slug: "open_meteo", name: "Open-Meteo" },
    retrieved_at: "2026-10-31T09:00:00Z",
    note: "Provider model output, not a station observation.",
    reason: null,
  },
  rain: {
    state: "AVAILABLE",
    next_24h_total_mm: 30,
    next_24h_max_probability_pct: 95,
    peak_hour: "2026-10-31T12:00:00Z",
    peak_hour_mm: 18,
    source: { slug: "open_meteo", name: "Open-Meteo" },
    retrieved_at: "2026-10-31T09:00:00Z",
    note: "Forecast rainfall is model output.",
    reason: null,
  },
  recent_rain: {
    state: "AVAILABLE",
    max_daily_mm: 12,
    total_mm: 18,
    window_hours: 48,
    days_covered: 2,
    source: { slug: "open_meteo", name: "Open-Meteo" },
    observed_at: "2026-10-31T00:00:00Z",
    note: "Daily model/archive value, not a rain gauge.",
  },
  waterlogging: {
    state: "AVAILABLE",
    level: "elevated",
    label: "Elevated waterlogging signal",
    points: 3,
    max_points: 8,
    method: {
      id: "rule_based_rain_and_reports_v1",
      version: "place-status-v1",
      label: "Rule-based waterlogging risk indicator",
      is_ml: false,
      description: "Adds transparent points for forecast rain, recent rain and nearby reports.",
    },
    inputs: [
      {
        key: "forecast_rain_24h",
        label: "Forecast rain, next 24 h",
        value: 30,
        unit: "mm",
        state: "AVAILABLE",
        source: { slug: "open_meteo", name: "Open-Meteo" },
        observed_at: "2026-10-31T09:00:00Z",
        contribution: 2,
        detail: "Hourly forecast summed over the next 24 hours.",
      },
    ],
    drivers: ["Forecast rain, next 24 h: 30 mm"],
    reports: { window_hours: 24, radius_km: 2.5, verified: 1, unverified: 0, total: 1 },
    caveats: [
      "This is a rule-based risk indicator built from rainfall and nearby reports. It is not a trained ML model, not a probability, and not a flood forecast.",
    ],
  },
  heat: {
    state: "PARTIAL",
    air: {
      state: "AVAILABLE",
      temperature_c: 31.2,
      apparent_temperature_c: 37.4,
      value_c: 37.4,
      value_label: "apparent temperature",
      level: "caution",
      observed_at: "2026-10-31T09:00:00Z",
      retrieved_at: "2026-10-31T09:00:00Z",
      source: { slug: "open_meteo", name: "Open-Meteo" },
      note: "Model output, not a station measurement.",
      reason: null,
    },
    land_surface: {
      state: "UNAVAILABLE",
      latest_date: null,
      nearest_cell_lst_c: null,
      nearest_cell_code: null,
      distance_km: null,
      city_p90_c: null,
      observed_count: 0,
      source: { slug: "landsat", name: "USGS Landsat" },
      note: "Land-surface temperature is not air temperature.",
      reason: "No Landsat land-surface observations have been ingested.",
    },
  },
  air_quality: {
    state: "UNAVAILABLE",
    station: null,
    measurement: null,
    distance_km: null,
    level: "unknown",
    source: {},
    note: "Station values are point measurements.",
    reason: "No CPCB monitoring stations have been ingested. CPCB_API_KEY is not configured.",
  },
  alerts: {
    state: "UNAVAILABLE",
    count: 0,
    results: [],
    source: {},
    last_success_at: null,
    note: "Absence of a warning is not proof that conditions are safe.",
    reason: "IMD_API_KEY is not configured; the official warning feed is unavailable.",
  },
  reports: {
    state: "AVAILABLE",
    window_hours: 72,
    radius_km: 2.5,
    total: 1,
    verified: 1,
    unverified: 0,
    results: [report],
    note: "Public resident reports within 2.5 km.",
    reason: null,
  },
  coverage: {
    available: 3,
    total: 6,
    modules: [
      { key: "weather", label: "Weather", state: "AVAILABLE" },
      { key: "waterlogging", label: "Waterlogging signal", state: "AVAILABLE" },
      { key: "alerts", label: "Official alerts", state: "UNAVAILABLE" },
      { key: "air_quality", label: "Air quality", state: "UNAVAILABLE" },
      { key: "heat", label: "Heat", state: "PARTIAL" },
      { key: "reports", label: "Community reports", state: "AVAILABLE" },
    ],
  },
  disclaimer: "Decision support assembled from stored records. Not an official warning service.",
};

function renderPage() {
  vi.mocked(usePlaceStatus).mockReturnValue({
    data: payload,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof usePlaceStatus>);

  return render(
    <AuthContext.Provider
      value={{
        user: null,
        token: null,
        isAuthenticated: false,
        isModerator: false,
        isLoading: false,
        login: vi.fn(),
        register: vi.fn(),
        logout: vi.fn(),
        updateUser: vi.fn(),
        refreshUser: vi.fn(),
      }}
    >
      <MemoryRouter initialEntries={["/place/kolkata/park-street"]}>
        <Routes>
          <Route path="/place/:areaSlug/:neighbourhoodSlug" element={<PlaceStatusPage />} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe("place status", () => {
  it("routes areas and neighbourhoods to the same area-first page", () => {
    expect(
      placePath({ type: "area", slug: "kolkata", area_slug: "kolkata" }),
    ).toBe("/place/kolkata");
    expect(
      placePath({ type: "neighbourhood", slug: "park-street", area_slug: "kolkata" }),
    ).toBe("/place/kolkata/park-street");
  });

  it("shows the place label, rule-based signal and honest gaps", () => {
    renderPage();
    expect(screen.getByRole("heading", { name: "Park Street, Kolkata" })).toBeInTheDocument();
    expect(screen.getByText("Worth checking before you travel")).toBeInTheDocument();
    expect(screen.getAllByText("Elevated waterlogging signal").length).toBeGreaterThan(0);
    expect(screen.getByText(/not a trained ML model/)).toBeInTheDocument();
    expect(screen.getAllByText(/CPCB_API_KEY is not configured/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Community reports").length).toBeGreaterThan(0);
  });
});
