import { describe, expect, it } from "vitest";

import {
  formatNumber,
  formatPercent,
  formatTemperature,
  formatWithUnit,
  titleCase,
  truncate,
} from "../lib/format";

describe("format helpers", () => {
  it("converts Celsius to Fahrenheit without hiding the unit", () => {
    expect(formatTemperature(30, "C", 0)).toContain("30°C");
    expect(formatTemperature(30, "F", 0)).toContain("86°F");
  });

  it("returns an em dash for missing values rather than zero", () => {
    expect(formatTemperature(null)).toBe("—");
    expect(formatWithUnit(undefined, "mm")).toBe("—");
    expect(formatPercent(Number.NaN)).toBe("—");
    expect(formatNumber(null)).toBe("—");
  });

  it("normalises enum-like labels for display", () => {
    expect(titleCase("UNDER_REVIEW")).toBe("Under Review");
    expect(titleCase("air_quality")).toBe("Air Quality");
    expect(titleCase(null)).toBe("—");
  });

  it("truncates long text deterministically", () => {
    expect(truncate("abcdefghij", 5)).toBe("abcde…");
    expect(truncate("short", 10)).toBe("short");
  });
});
