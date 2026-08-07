/**
 * Reads the design-token CSS variables (see src/index.css) as usable color
 * strings, for chart libraries (lightweight-charts, recharts) that need a
 * real CSS color value rather than a Tailwind class.
 *
 * Comma-separated `rgb(r, g, b)` is used deliberately over the modern
 * space-separated `rgb(r g b)` syntax: lightweight-charts' internal color
 * parser (fancy-canvas) does not accept the space-separated form and throws
 * "Cannot parse color" at render time — verified by an actual browser run,
 * not by reading its source.
 */
function readVar(name: string): string {
  const value = getComputedStyle(document.documentElement).getPropertyValue(`--color-${name}`).trim();
  if (!value) return "#000000";
  const [r, g, b] = value.split(/\s+/);
  return `rgb(${r}, ${g}, ${b})`;
}

export function getChartTokens() {
  return {
    surfaceCard: readVar("surface-card"),
    surfaceRaised: readVar("surface-raised"),
    inkPrimary: readVar("ink-primary"),
    inkSecondary: readVar("ink-secondary"),
    inkMuted: readVar("ink-muted"),
    gridline: readVar("gridline"),
    baseline: readVar("baseline"),
    accent: readVar("accent"),
    bull: readVar("bull"),
    bear: readVar("bear"),
    deltaGood: readVar("delta-good"),
    deltaBad: readVar("delta-bad"),
    series: [
      readVar("series-1"),
      readVar("series-2"),
      readVar("series-3"),
      readVar("series-4"),
      readVar("series-5"),
      readVar("series-6"),
      readVar("series-7"),
      readVar("series-8"),
    ],
  };
}
