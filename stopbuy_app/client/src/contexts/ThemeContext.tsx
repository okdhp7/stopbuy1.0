import React, { createContext, useContext, useEffect, useState } from "react";

type Theme = "light" | "dark";

interface ThemeContextType {
  theme: Theme;
  toggleTheme?: () => void;
  switchable: boolean;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

interface ThemeProviderProps {
  children: React.ReactNode;
  defaultTheme?: Theme;
  switchable?: boolean;
}

export function ThemeProvider({
  children,
  defaultTheme = "dark",
  switchable = false,
}: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(() => {
    if (switchable) {
      const stored = localStorage.getItem("stopbuy-theme");
      return (stored as Theme) || defaultTheme;
    }
    return defaultTheme;
  });

  useEffect(() => {
    const root = document.documentElement;
    // 두 클래스 모두 제거 후 현재 테마 클래스 추가
    root.classList.remove("dark", "light");
    root.classList.add(theme);

    if (switchable) {
      localStorage.setItem("stopbuy-theme", theme);
    }
  }, [theme, switchable]);

  const toggleTheme = switchable
    ? () => {
        setTheme(prev => (prev === "dark" ? "light" : "dark"));
      }
    : undefined;

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, switchable }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
}
