export function formatNumber(value) {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(value ?? 0);
}

export function timeAgo(iso) {
  if (!iso) return "";
  const seconds = (Date.now() - new Date(iso).getTime()) / 1000;
  const units = [["year", 31536000], ["month", 2592000], ["week", 604800], ["day", 86400], ["hour", 3600], ["minute", 60]];
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  for (const [unit, size] of units) {
    if (seconds >= size) return formatter.format(-Math.floor(seconds / size), unit);
  }
  return formatter.format(0, "minute");
}

export function shortDate(isoDay) {
  return new Date(`${isoDay}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

// A three-letter course code for a subject, e.g. "Social Studies" -> "SST".
export function subjectCode(title = "") {
  const words = title.replace(/[^A-Za-z ]/g, " ").trim().split(/\s+/).filter(Boolean);
  if (!words.length) return "GEN";
  if (words.length === 1) return words[0].slice(0, 3).toUpperCase();
  return (words[0][0] + words[1].slice(0, 2)).toUpperCase(); // "Social Studies" -> "SST"
}
