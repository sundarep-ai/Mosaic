/**
 * Pure helpers behind the Landing-page insight preview: picking which alerts
 * to surface (recurring alerts first, category trend alerts fill the rest)
 * and building the one-line forecast sentence.
 */

export function selectTopAlerts(recurringAlerts = [], categoryTrendAlerts = [], max = 2) {
  const recurring = recurringAlerts.slice(0, max);
  const remaining = Math.max(0, max - recurring.length);
  const trend = categoryTrendAlerts.slice(0, remaining);
  return { recurring, trend };
}

export function getForecastLine(forecast, fmt) {
  if (!forecast) return null;
  // `on_pace.estimated_total` (MTD actual + remaining scheduled bills + the
  // remaining-days variable rate) is the actual "this month" number; older
  // backends without it fall back to `total_forecast`, which is really next
  // month's forecast but was the closest available figure before this field
  // existed.
  const onPaceTotal = forecast.on_pace?.estimated_total;
  const amount = onPaceTotal > 0 ? onPaceTotal : forecast.total_forecast;
  if (!(amount > 0)) return null;
  return `On track for ~${fmt(amount)} this month`;
}
