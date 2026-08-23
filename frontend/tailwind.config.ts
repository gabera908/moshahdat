import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#B87333",
          50: "#FBF3EA",
          100: "#F5E2CC",
          200: "#EAC49A",
          300: "#DFA667",
          400: "#CB8840",
          500: "#B87333",
          600: "#9A5F28",
          700: "#7B4B1F",
          800: "#5C3817",
          900: "#3D250F",
        },
        secondary: {
          DEFAULT: "#2C3E50",
          light: "#34495E",
        },
        surface: {
          light: "#FFFFFF",
          lightAlt: "#F6F7F9",
          dark: "#0F1115",
          card: "#181B21",
          cardHover: "#1F232B",
        },
      },
      fontFamily: {
        sans: [
          "Cairo",
          "Tajawal",
          "Segoe UI",
          "Tahoma",
          "system-ui",
          "sans-serif",
        ],
      },
      borderRadius: {
        xl: "0.875rem",
        "2xl": "1.25rem",
      },
      boxShadow: {
        card: "0 4px 20px -6px rgba(0,0,0,0.25)",
        glow: "0 0 24px -6px rgba(184,115,51,0.45)",
      },
    },
  },
  plugins: [],
};

export default config;
