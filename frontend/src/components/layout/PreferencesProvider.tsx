import { useEffect, useMemo, useState, type ReactNode } from "react";

import { applyTheme, currentArea, PreferencesContext, saveArea, storedTheme, type ThemeChoice } from "../../lib/preferences";

export function PreferencesProvider({ children }: { children: (area: string) => ReactNode }) {
  const [area, setAreaState] = useState(currentArea);
  const [theme, setTheme] = useState<ThemeChoice>(storedTheme);

  useEffect(() => {
    applyTheme(theme);
    const media = window.matchMedia?.("(prefers-color-scheme: dark)");
    const update = () => applyTheme(theme);
    media?.addEventListener("change", update);
    return () => media?.removeEventListener("change", update);
  }, [theme]);

  const value = useMemo(
    () => ({
      area,
      theme,
      setTheme,
      setArea: (slug: string) => {
        saveArea(slug);
        setAreaState(slug);
      },
    }),
    [area, theme],
  );

  return <PreferencesContext.Provider value={value}>{children(area)}</PreferencesContext.Provider>;
}
