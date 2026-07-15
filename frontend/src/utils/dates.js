/**
 * Format a Date using its local calendar date as YYYY-MM-DD.
 *
 * Never use `date.toISOString().split("T")[0]` for this — toISOString()
 * converts to UTC first, which silently rolls the date backward or forward
 * a day whenever the local offset pushes the instant across midnight UTC.
 */
export function toLocalISODate(date = new Date()) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}
