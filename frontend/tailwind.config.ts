import type { Config } from "tailwindcss";

// Tokens are defined as CSS variables in globals.css (ported from design/index.html).
// Tailwind color/font names map to those vars so both `bg-accent` utilities and raw
// `var(--accent)` work. Preflight is disabled during the Mantine→Tailwind transition
// (re-evaluated in Phase 3); our own base resets live in globals.css.
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  corePlugins: { preflight: false },
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        black: "var(--black)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        "surface-3": "var(--surface-3)",
        text: "var(--text)",
        muted: "var(--muted)",
        "muted-2": "var(--muted-2)",
        border: "var(--border)",
        "border-2": "var(--border-2)",
        accent: "var(--accent)",
        "accent-soft": "var(--accent-soft)",
        "accent-2": "var(--accent-2)",
        success: "var(--success)",
        neutral: "var(--neutral)",
        danger: "var(--danger)",
        "inv-bg": "var(--inv-bg)",
        "inv-text": "var(--inv-text)",
      },
      borderColor: { DEFAULT: "var(--border)" },
      fontFamily: {
        display: ["var(--font-display)", "monospace"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      borderRadius: { none: "0", sm: "2px", DEFAULT: "4px", md: "6px", lg: "8px" },
      maxWidth: { content: "1280px" },
      spacing: { sidebar: "var(--sidebar-w)", header: "var(--header-h)" },
    },
  },
  plugins: [],
};

export default config;
