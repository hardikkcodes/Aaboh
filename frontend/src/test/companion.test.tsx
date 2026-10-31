import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { translate } from "../lib/i18n";
import { useAccurateLocation } from "../lib/useAccurateLocation";

function reading(accuracy: number, latitude = 22.5726) {
  return { coords: { latitude, longitude: 88.3639, accuracy } } as GeolocationPosition;
}

function mockGeolocation() {
  let onPosition: PositionCallback = () => undefined;
  let onError: PositionErrorCallback = () => undefined;
  const geolocation = {
    watchPosition: vi.fn((success: PositionCallback, failure: PositionErrorCallback) => {
      onPosition = success;
      onError = failure;
      return 7;
    }),
    clearWatch: vi.fn(),
  };
  Object.defineProperty(navigator, "geolocation", { value: geolocation, configurable: true });
  return { geolocation, emit: (position: GeolocationPosition) => onPosition(position), fail: (code: number) => onError({ code } as GeolocationPositionError) };
}

afterEach(() => {
  vi.useRealTimers();
});

describe("accurate location", () => {
  it("keeps the most accurate reading and stops at a good fix", () => {
    const { geolocation, emit } = mockGeolocation();
    const finished = vi.fn();
    const { result } = renderHook(() => useAccurateLocation(finished));

    act(() => result.current.locate());
    act(() => emit(reading(900)));
    expect(result.current.status).toBe("locating");
    act(() => emit(reading(60, 22.57301)));
    act(() => emit(reading(300)));
    expect(result.current.fix).toEqual({ latitude: 22.57301, longitude: 88.3639, accuracy: 60 });

    act(() => emit(reading(12, 22.57312)));
    expect(result.current.status).toBe("ready");
    expect(result.current.fix?.accuracy).toBe(12);
    expect(geolocation.clearWatch).toHaveBeenCalledWith(7);
    expect(finished).toHaveBeenCalledOnce();
  });

  it("uses the best reading when time runs out", () => {
    vi.useFakeTimers();
    const { emit } = mockGeolocation();
    const { result } = renderHook(() => useAccurateLocation());

    act(() => result.current.locate());
    act(() => emit(reading(80)));
    act(() => {
      vi.advanceTimersByTime(12_000);
    });

    expect(result.current.status).toBe("ready");
    expect(result.current.fix?.accuracy).toBe(80);
  });

  it("reports denied permission", () => {
    const { fail } = mockGeolocation();
    const { result } = renderHook(() => useAccurateLocation());

    act(() => result.current.locate());
    act(() => fail(1));

    expect(result.current.status).toBe("error");
    expect(result.current.problem).toBe("denied");
  });
});

describe("translation", () => {
  it("translates and fills in values", () => {
    expect(translate("bn", "Today in {place}", { place: "কলকাতা" })).toBe("আজ কলকাতা-এ");
  });

  it("falls back to English when a string has no translation", () => {
    expect(translate("bn", "Something new")).toBe("Something new");
    expect(translate("bn", "tip.unknown", {}, "Fallback text")).toBe("Fallback text");
    expect(translate("en", "Today in {place}", { place: "Kolkata" })).toBe("Today in Kolkata");
  });
});
