import { useState, useEffect } from 'react';

const STORAGE_KEY = 'manhwarank-theme';
const THEMES = { DARK: 'dark', LIGHT: 'light' };

export function useTheme() {
  const [theme, setTheme] = useState(() => {
    const storedTheme = localStorage.getItem(STORAGE_KEY);
    if (storedTheme) {
      return storedTheme;
    }
    return window.matchMedia('(prefers-color-scheme: light)').matches ? THEMES.LIGHT : THEMES.DARK;
  });

  useEffect(() => {
    const root = document.documentElement;
    if (theme === THEMES.LIGHT) {
      root.setAttribute('data-theme', 'light');
    } else {
      root.removeAttribute('data-theme');
    }
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => (prev === THEMES.DARK ? THEMES.LIGHT : THEMES.DARK));
  };

  return { theme, toggleTheme, isDark: theme === THEMES.DARK, isLight: theme === THEMES.LIGHT };
}
