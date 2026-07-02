const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 31536000],
  ["month", 2592000],
  ["week", 604800],
  ["day", 86400],
  ["hour", 3600],
  ["minute", 60],
];

const rtf = new Intl.RelativeTimeFormat("en", { numeric: "always", style: "narrow" });

function compact(n: number): string {
  return n >= 1000 ? `${Math.round(n / 1000)}k` : String(n);
}

export function formatSalary(
  min: number | null | undefined,
  max: number | null | undefined,
  currency: string | null | undefined,
): string | null {
  if (min == null && max == null) return null;
  const cur = currency ?? "";
  if (min != null && max != null && min !== max)
    return `${compact(min)}–${compact(max)} ${cur}`.trim();
  return `${compact((min ?? max)!)} ${cur}`.trim();
}

export function relativeTime(iso: string | null): string {
  if (!iso) return "";
  const seconds = (Date.parse(iso) - Date.now()) / 1000;
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size) {
      return rtf.format(Math.round(seconds / size), unit);
    }
  }
  return "just now";
}
