import { createContext, useContext } from "react";

export type ThemeChoice = "system" | "light" | "dark";

const AREA_KEY = "climatesense.area";
const THEME_KEY = "climatesense.theme";
const EXTRA_CARE_KEY = "climatesense.extraCare";
export const DEFAULT_AREA = "kolkata";

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // The choice simply lasts for this visit.
  }
}

export function currentArea(): string {
  return read(AREA_KEY) ?? DEFAULT_AREA;
}

export function saveArea(slug: string): void {
  write(AREA_KEY, slug);
}

export function extraCareOn(): boolean {
  return read(EXTRA_CARE_KEY) === "on";
}

export function saveExtraCare(on: boolean): void {
  write(EXTRA_CARE_KEY, on ? "on" : "off");
}

export function storedTheme(): ThemeChoice {
  const value = read(THEME_KEY);
  return value === "light" || value === "dark" ? value : "system";
}

export function applyTheme(choice: ThemeChoice): void {
  write(THEME_KEY, choice);
  const dark = choice === "dark" || (choice === "system" && window.matchMedia?.("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", Boolean(dark));
}

export const PreferencesContext = createContext<{
  area: string;
  setArea: (slug: string) => void;
  theme: ThemeChoice;
  setTheme: (theme: ThemeChoice) => void;
}>({ area: DEFAULT_AREA, setArea: () => undefined, theme: "system", setTheme: () => undefined });

export function usePreferences() {
  return useContext(PreferencesContext);
}
