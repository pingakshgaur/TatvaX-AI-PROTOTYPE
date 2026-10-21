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

// Days follow the school's clock (sent by the server), so "today", "overdue" and due dates agree
// with the server whatever time zone the device is set to.
let schoolOffsetMinutes = null;

export function setSchoolClock(minutes) {
  schoolOffsetMinutes = Number.isFinite(minutes) ? minutes : null;
}

// The school's date as YYYY-MM-DD, optionally a number of days from today.
export function schoolToday(addDays = 0) {
  const offset = schoolOffsetMinutes ?? -new Date().getTimezoneOffset();
  const d = new Date(Date.now() + offset * 60000);
  d.setUTCDate(d.getUTCDate() + addDays);
  return d.toISOString().slice(0, 10);
}

// Whole days from the school's today to a YYYY-MM-DD date (negative when it has passed).
export function daysFromToday(isoDay) {
  return Math.round((Date.parse(`${isoDay}T00:00:00Z`) - Date.parse(`${schoolToday()}T00:00:00Z`)) / 86400000);
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
