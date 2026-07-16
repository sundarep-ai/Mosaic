/**
 * Pure helpers behind the redesigned Insights page.
 *
 * The page is organized into two tiers: a prioritized "Needs your attention"
 * area (alerts + anomalies that a person should act on) and a "Trends &
 * patterns" area (the always-on analytical sections). To keep the page from
 * feeling overwhelming, an analytical section is rendered only when it
 * actually has data — these predicates are the single source of truth for
 * that "does this section have anything to show" decision, so the page and
 * its tests agree on it.
 */

/**
 * Group the attention-tier signals and report whether any of them exist.
 * Order mirrors how they're surfaced: price-step alerts, new subscriptions,
 * category trends, then anomalies.
 */
export function getAttention(data = {}) {
  const recurring_alerts = data.recurring_alerts || [];
  const new_subscription_alerts = data.new_subscription_alerts || [];
  const category_trend_alerts = data.category_trend_alerts || [];
  const anomalies = data.anomalies || [];
  const hasAny =
    recurring_alerts.length +
      new_subscription_alerts.length +
      category_trend_alerts.length +
      anomalies.length >
    0;
  return {
    recurring_alerts,
    new_subscription_alerts,
    category_trend_alerts,
    anomalies,
    hasAny,
  };
}

/** True when weekend/weekday has at least one transaction to summarize. */
export function hasWeekendData(weekend) {
  const y = weekend?.your_expense;
  if (!y) return false;
  return (y.weekday.count || 0) + (y.weekend.count || 0) > 0;
}

/**
 * True when income insights have any real income logged — mirrors the same
 * check `IncomeInsightsSection` uses internally so we never render an empty
 * income section.
 */
export function hasIncomeData(income) {
  if (!income) return false;
  const trend = income.savings_rate?.trend || [];
  const current = income.savings_rate?.current_month;
  return trend.some((s) => s.income > 0) || (current?.income || 0) > 0;
}

/**
 * Which Tier-2 analytical sections have data worth rendering. `incomeEnabled`
 * is the per-user preference — income insights are hidden entirely when it's
 * off, regardless of whether income data exists.
 */
export function getSectionVisibility(data = {}, incomeEnabled = false) {
  const forecast = data.forecast || {};
  return {
    forecast: (forecast.total_forecast || 0) > 0,
    recurring: (data.recurring_expenses || []).length > 0,
    weekend: hasWeekendData(data.weekend_vs_weekday),
    topGrowing: (data.top_growing_categories || []).length > 0,
    income: Boolean(incomeEnabled && hasIncomeData(data.income_insights)),
  };
}

/** True when at least one Tier-2 section is visible. */
export function hasAnySection(visibility) {
  return Object.values(visibility).some(Boolean);
}

/**
 * One-line "on pace" headline for the current month. Prefers
 * `on_pace.estimated_total` (MTD actual + remaining scheduled bills + the
 * remaining-days variable rate — the accurate current-month number), falling
 * back to `total_forecast` for older backends that predate that field (that
 * figure is really *next* month's forecast, but it was the closest available).
 */
export function getForecastLine(forecast, fmt) {
  if (!forecast) return null;
  const onPaceTotal = forecast.on_pace?.estimated_total;
  const amount = onPaceTotal > 0 ? onPaceTotal : forecast.total_forecast;
  if (!(amount > 0)) return null;
  return `On track for ~${fmt(amount)} this month`;
}
