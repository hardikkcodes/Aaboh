import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f4f7f6",
          100: "#e3ebe8",
          200: "#c8d8d3",
          300: "#9fbdb4",
          400: "#6f9a8f",
          500: "#4f7d71",
          600: "#3c645a",
          700: "#325149",
          800: "#2a423d",
          900: "#243733",
          950: "#111f1c",
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
        mist: "#f7faf9",
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "system-ui", "sans-serif"],
        display: ["Fraunces", "Georgia", "serif"],
      },
      boxShadow: {
        panel: "0 1px 2px rgba(17,31,28,0.05), 0 12px 32px -24px rgba(17,31,28,0.35)",
      },
    },
  },
  plugins: [],
} satisfies Config;
