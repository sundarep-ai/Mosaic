import { useState, useEffect } from "react";
import { getInsights } from "../api/expenses";
import { useTheme } from "../ThemeContext";
import { useCurrency } from "../CurrencyContext";
import { getChartColors, getTooltipStyles } from "../utils/chartConfig";
import { useIncomeMode } from "../hooks/useIncomeMode";
import {
  getAttention,
  getSectionVisibility,
  hasAnySection,
  getForecastLine,
} from "../utils/insightsView";
import AlertBanners from "../components/insights/AlertBanners";
import ForecastSection from "../components/insights/ForecastSection";
import AnomaliesSection from "../components/insights/AnomaliesSection";
import RecurringExpenses from "../components/insights/RecurringExpenses";
import WeekendVsWeekday from "../components/insights/WeekendVsWeekday";
import TopGrowingCategories from "../components/insights/TopGrowingCategories";
import IncomeInsightsSection from "../components/insights/IncomeInsightsSection";
import EmptyState from "../components/insights/EmptyState";

export default function Insights() {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const CHART_COLORS = getChartColors(isDark);
  const { tooltipStyle, tooltipItemStyle, tooltipLabelStyle } = getTooltipStyles(isDark);
  const { incomeEnabled } = useIncomeMode();
  const { fmt } = useCurrency();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const result = await getInsights();
        setData(result);
      } catch {
        setError("Could not load insights. Is the server running?");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-error text-sm">
        {error}
      </div>
    );
  }

  const emptyWeekendData = {
    weekday: { total: 0, count: 0, by_category: [] },
    weekend: { total: 0, count: 0, by_category: [] },
  };

  const {
    recurring_expenses = [],
    weekend_vs_weekday = { your_expense: emptyWeekendData, shared_expense: emptyWeekendData },
    forecast = { recurring_total: 0, variable_total: 0, total_forecast: 0, last_month_total: 0, change_vs_last_month_pct: 0, shared_total_forecast: 0, by_category: [] },
    top_growing_categories = [],
    income_insights = null,
    mode = "shared",
  } = data || {};

  // Attention tier: the alerts + anomalies a person should act on.
  const attention = getAttention(data);
  // Trends tier: analytical sections rendered only when they hold real data,
  // so a light/new account no longer sees a wall of empty-state placeholders.
  const visibility = getSectionVisibility(data, incomeEnabled);
  const anySection = hasAnySection(visibility);
  const onPaceLine = getForecastLine(forecast, fmt);
  const chartProps = { CHART_COLORS, isDark, tooltipStyle, tooltipItemStyle, tooltipLabelStyle };

  const hasAnything = attention.hasAny || anySection || Boolean(onPaceLine);

  return (
    <div className="space-y-10">
      {/* Header */}
      <section>
        <h1 className="font-headline text-3xl font-bold tracking-tight text-on-surface">
          Smart Insights
        </h1>
        <p className="text-on-surface-variant font-medium">
          What needs your attention, and the patterns behind your spending.
        </p>
      </section>

      {/* On-pace headline — the accurate current-month projection */}
      {onPaceLine && (
        <div className="bg-primary text-on-primary rounded-[2rem] p-6 md:p-8 flex items-center gap-4 relative overflow-hidden">
          <span className="material-symbols-outlined text-3xl">speed</span>
          <div>
            <p className="font-label text-xs uppercase tracking-[0.2em] text-on-primary/70 font-bold">
              This month
            </p>
            <p className="font-headline text-2xl font-extrabold">{onPaceLine}</p>
          </div>
          <div className="absolute top-0 right-0 w-48 h-48 bg-on-primary/10 blur-[80px] rounded-full -mr-16 -mt-16" />
        </div>
      )}

      {/* ── Tier 1: Needs your attention ── */}
      {attention.hasAny && (
        <section className="space-y-4">
          <h2 className="font-headline text-xl font-bold flex items-center gap-2">
            <span className="material-symbols-outlined text-tertiary">notifications_active</span>
            Needs your attention
          </h2>
          <AlertBanners
            recurring_alerts={attention.recurring_alerts}
            new_subscription_alerts={attention.new_subscription_alerts}
            category_trend_alerts={attention.category_trend_alerts}
            mode={mode}
          />
          <AnomaliesSection anomalies={attention.anomalies} mode={mode} />
        </section>
      )}

      {/* ── Tier 2: Trends & patterns (only sections with data) ── */}
      {anySection && (
        <section className="space-y-10">
          <h2 className="font-headline text-xl font-bold flex items-center gap-2 border-t border-surface-container-high pt-8">
            <span className="material-symbols-outlined text-primary">insights</span>
            Trends &amp; patterns
          </h2>
          {visibility.forecast && (
            <ForecastSection forecast={forecast} mode={mode} {...chartProps} />
          )}
          {visibility.recurring && (
            <RecurringExpenses recurring_expenses={recurring_expenses} mode={mode} />
          )}
          {visibility.weekend && (
            <WeekendVsWeekday weekend_vs_weekday={weekend_vs_weekday} mode={mode} {...chartProps} />
          )}
          {visibility.topGrowing && (
            <TopGrowingCategories top_growing_categories={top_growing_categories} mode={mode} />
          )}
          {visibility.income && (
            <IncomeInsightsSection data={income_insights} {...chartProps} />
          )}
        </section>
      )}

      {/* Nothing to show yet */}
      {!hasAnything && (
        <EmptyState
          icon="auto_awesome"
          message="No insights yet. Keep logging expenses — recurring bills, spending trends, and unusual charges will appear here automatically."
        />
      )}
    </div>
  );
}
