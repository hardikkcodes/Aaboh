const KOLKATA_TZ = "Asia/Kolkata";

function locale(): string {
  return document.documentElement.lang === "bn" ? "bn-IN" : "en-IN";
}

export function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDateTime(value: string | null | undefined): string {
  const date = parseDate(value);
  if (!date) return "—";
  return new Intl.DateTimeFormat(locale(), {
    timeZone: KOLKATA_TZ,
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  }).format(date);
}

export function formatDate(value: string | null | undefined): string {
  const date = parseDate(value);
  if (!date) return "—";
  return new Intl.DateTimeFormat(locale(), {
    timeZone: KOLKATA_TZ,
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function formatDay(value: string | null | undefined): string {
  const date = parseDate(value);
  if (!date) return "—";
  return new Intl.DateTimeFormat(locale(), {
    timeZone: KOLKATA_TZ,
    weekday: "short",
    day: "numeric",
    month: "short",
  }).format(date);
}

export function formatTime(value: string | null | undefined): string {
  const date = parseDate(value);
  if (!date) return "—";
  return new Intl.DateTimeFormat(locale(), {
    timeZone: KOLKATA_TZ,
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  }).format(date);
}

export function formatHour(value: string | null | undefined): string {
  const date = parseDate(value);
  if (!date) return "—";
  return new Intl.DateTimeFormat(locale(), {
    timeZone: KOLKATA_TZ,
    hour: "numeric",
    hour12: true,
  }).format(date);
}

export function formatRelative(value: string | null | undefined): string {
  const date = parseDate(value);
  if (!date) return "never";
  const diffMs = date.getTime() - Date.now();
  const diffMinutes = Math.round(diffMs / 60_000);
  const formatter = new Intl.RelativeTimeFormat(locale(), { numeric: "auto" });
  if (Math.abs(diffMinutes) < 60) return formatter.format(diffMinutes, "minute");
  const diffHours = Math.round(diffMinutes / 60);
  if (Math.abs(diffHours) < 48) return formatter.format(diffHours, "hour");
  const diffDays = Math.round(diffHours / 24);
  if (Math.abs(diffDays) < 45) return formatter.format(diffDays, "day");
  const diffMonths = Math.round(diffDays / 30);
  if (Math.abs(diffMonths) < 18) return formatter.format(diffMonths, "month");
  return formatter.format(Math.round(diffDays / 365), "year");
}

export function formatNumber(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat(locale(), {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

export function formatTemperature(
  value: number | null | undefined,
  unit: "C" | "F" = "C",
  digits = 1,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (unit === "F") {
    return `${formatNumber(value * (9 / 5) + 32, digits)}°F`;
  }
  return `${formatNumber(value, digits)}°C`;
}

export function formatWithUnit(
  value: number | null | undefined,
  unit: string,
  digits = 1,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${formatNumber(value, digits)}${unit ? ` ${unit}` : ""}`;
}

export function formatPercent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${formatNumber(value, digits)}%`;
}

export function titleCase(value: string | null | undefined): string {
  if (!value) return "—";
  return value
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function cn(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

export function truncate(value: string, length = 160): string {
  if (value.length <= length) return value;
  return `${value.slice(0, length).trimEnd()}…`;
}

export function toLocalInputValue(value: Date = new Date()): string {
  const offset = value.getTimezoneOffset();
  const local = new Date(value.getTime() - offset * 60_000);
  return local.toISOString().slice(0, 16);
}
