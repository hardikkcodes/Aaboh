import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "rgb(var(--ink-50) / <alpha-value>)",
          100: "rgb(var(--ink-100) / <alpha-value>)",
          200: "rgb(var(--ink-200) / <alpha-value>)",
          300: "rgb(var(--ink-300) / <alpha-value>)",
          400: "rgb(var(--ink-400) / <alpha-value>)",
          500: "rgb(var(--ink-500) / <alpha-value>)",
          600: "rgb(var(--ink-600) / <alpha-value>)",
          700: "rgb(var(--ink-700) / <alpha-value>)",
          800: "rgb(var(--ink-800) / <alpha-value>)",
          900: "rgb(var(--ink-900) / <alpha-value>)",
          950: "rgb(var(--ink-950) / <alpha-value>)",
        },
        ember: {
          50: "#fdf7ed",
          100: "#f9ebd2",
          200: "#f2d4a3",
          300: "#e9b76b",
          400: "#e09a42",
          500: "#d47f26",
          600: "#bb621b",
          700: "#984818",
          800: "#7c3a19",
          900: "#663117",
        },
        mist: "rgb(var(--mist) / <alpha-value>)",
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "system-ui", "sans-serif"],
        display: ["Inter", "Segoe UI", "system-ui", "sans-serif"],
      },
      boxShadow: {
        panel: "0 1px 2px rgba(17,31,28,0.05), 0 12px 32px -24px rgba(17,31,28,0.35)",
      },
    },
  },
  plugins: [],
} satisfies Config;
