import { useEffect, useState } from "react";

const THEME_KEY = "dsa-mentor-theme";

export type Theme = "dark" | "light";

export function getTheme(): Theme {
  const saved = localStorage.getItem(THEME_KEY);
  return saved === "light" ? "light" : "dark";
}

export function applyTheme(theme: Theme): void {
  localStorage.setItem(THEME_KEY, theme);
  document.documentElement.classList.toggle("dark", theme === "dark");
  window.dispatchEvent(new CustomEvent<Theme>("theme-change", { detail: theme }));
}

export function useTheme(): { isDark: boolean; toggleTheme: () => void } {
  const [isDark, setIsDark] = useState<boolean>(() => getTheme() === "dark");

  useEffect(() => {
    const handler = (event: Event) => {
      setIsDark((event as CustomEvent<Theme>).detail === "dark");
    };
    window.addEventListener("theme-change", handler);
    return () => window.removeEventListener("theme-change", handler);
  }, []);

  const toggleTheme = () => {
    applyTheme(isDark ? "light" : "dark");
  };

  return { isDark, toggleTheme };
}

