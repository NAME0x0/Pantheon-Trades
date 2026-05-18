"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { motion } from "framer-motion";

import { cn } from "@/lib/utils";

/**
 * Light/dark toggle.
 *
 * No next-themes dep — single CSS class on <html>, persisted to
 * localStorage, initial value seeded from prefers-color-scheme. The
 * pre-hydration script in <head> prevents the first-paint flash.
 */
export function ThemeToggle({ className }: { className?: string }) {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    const root = document.documentElement;
    setTheme(root.classList.contains("light") ? "light" : "dark");
  }, []);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    const root = document.documentElement;
    if (next === "light") {
      root.classList.add("light");
      root.classList.remove("dark");
    } else {
      root.classList.add("dark");
      root.classList.remove("light");
    }
    try {
      localStorage.setItem("pantheon-theme", next);
    } catch {}
    setTheme(next);
  }

  // Button previews the theme it switches TO — when currently dark and
  // showing the Sun (light), button itself is light-themed; when currently
  // light and showing the Moon (dark), button itself is dark-themed.
  const previewClasses =
    theme === "dark"
      ? "border-amber-200/50 bg-amber-50 text-amber-900 hover:border-amber-300 hover:bg-amber-100"
      : "border-slate-700 bg-slate-950 text-amber-200 hover:border-amber-200/70 hover:bg-slate-900";

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
      className={cn(
        "group relative inline-flex h-9 w-9 items-center justify-center rounded-full border transition-all focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background",
        previewClasses,
        className,
      )}
    >
      <motion.span
        key={theme}
        initial={{ rotate: -90, opacity: 0, scale: 0.7 }}
        animate={{ rotate: 0, opacity: 1, scale: 1 }}
        exit={{ rotate: 90, opacity: 0, scale: 0.7 }}
        transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
        className="inline-flex"
      >
        {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
      </motion.span>
    </button>
  );
}

/**
 * Inline script for the document <head> that applies the persisted /
 * preferred theme before React hydrates. Prevents the dark↔light flash.
 */
export const themeInitScript = `
(function() {
  try {
    var stored = localStorage.getItem('pantheon-theme');
    var prefers = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    var theme = stored || 'dark';
    var root = document.documentElement;
    if (theme === 'light') { root.classList.add('light'); root.classList.remove('dark'); }
    else { root.classList.add('dark'); root.classList.remove('light'); }
  } catch (e) {}
})();
`;
