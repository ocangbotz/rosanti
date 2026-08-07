/** @type {import('tailwindcss').Config} */

// Wraps a CSS variable holding a space-separated RGB triplet (see
// src/index.css) so Tailwind's opacity modifiers work, e.g. `bg-bull/15`.
function rgbVar(name) {
  return `rgb(var(--color-${name}) / <alpha-value>)`;
}

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "sans-serif",
        ],
      },
      colors: {
        surface: {
          page: rgbVar("surface-page"),
          card: rgbVar("surface-card"),
          raised: rgbVar("surface-raised"),
        },
        ink: {
          primary: rgbVar("ink-primary"),
          secondary: rgbVar("ink-secondary"),
          muted: rgbVar("ink-muted"),
        },
        border: {
          DEFAULT: "rgb(var(--color-border) / var(--color-border-alpha))",
        },
        accent: {
          DEFAULT: rgbVar("accent"),
          hover: rgbVar("accent-hover"),
        },
        status: {
          good: rgbVar("status-good"),
          warning: rgbVar("status-warning"),
          serious: rgbVar("status-serious"),
          critical: rgbVar("status-critical"),
        },
        bull: rgbVar("bull"),
        bear: rgbVar("bear"),
        delta: {
          good: rgbVar("delta-good"),
          bad: rgbVar("delta-bad"),
        },
        series: {
          1: rgbVar("series-1"),
          2: rgbVar("series-2"),
          3: rgbVar("series-3"),
          4: rgbVar("series-4"),
          5: rgbVar("series-5"),
          6: rgbVar("series-6"),
          7: rgbVar("series-7"),
          8: rgbVar("series-8"),
        },
      },
    },
  },
  plugins: [],
};
