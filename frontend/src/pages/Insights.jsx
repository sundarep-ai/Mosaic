import { useState, useEffect } from "react";
import { getInsights } from "../api/expenses";
import { useTheme } from "../ThemeContext";
import { getChartColors, getTooltipStyles } from "../utils/chartConfig";
import { useIncomeMode } from "../hooks/useIncomeMode";
import AlertBanners from "../components/insights/AlertBanners";
import ForecastSection from "../components/insights/ForecastSection";
import AnomaliesSection from "../components/insights/AnomaliesSection";
import RecurringExpenses from "../components/insights/RecurringExpenses";
import WeekendVsWeekday from "../components/insights/WeekendVsWeekday";
import TopGrowingCategories from "../components/insights/TopGrowingCategories";
import IncomeInsightsSection from "../components/insights/IncomeInsightsSection";

export default function Insights() {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const CHART_COLORS = getChartColors(isDark);
  const { tooltipStyle, tooltipItemStyle, tooltipLabelStyle } = getTooltipStyles(isDark);
  const { incomeEnabled } = useIncomeMode();

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
    recurring_alerts = [],
    weekend_vs_weekday = { your_expense: emptyWeekendData, shared_expense: emptyWeekendData },
    category_trend_alerts = [],
    anomalies = [],
    forecast = { recurring_total: 0, variable_total: 0, total_forecast: 0, last_month_total: 0, change_vs_last_month_pct: 0, shared_total_forecast: 0, by_category: [] },
    top_growing_categories = [],
    income_insights = null,
    mode = "shared",
  } = data || {};

  const hasAlerts = recurring_alerts.length > 0 || category_trend_alerts.length > 0;
  const chartProps = { CHART_COLORS, isDark, tooltipStyle, tooltipItemStyle, tooltipLabelStyle };

  return (
    <div className="space-y-10">
      {/* Header */}
      <section>
        <h1 className="font-headline text-3xl font-bold tracking-tight text-on-surface">
          Smart Insights
        </h1>
        <p className="text-on-surface-variant font-medium">
          Automated analysis of your spending patterns.
        </p>
      </section>

      {hasAlerts && (
        <AlertBanners
          recurring_alerts={recurring_alerts}
          category_trend_alerts={category_trend_alerts}
          mode={mode}
        />
      )}

      <ForecastSection forecast={forecast} mode={mode} {...chartProps} />
      <AnomaliesSection anomalies={anomalies} mode={mode} />
      <RecurringExpenses recurring_expenses={recurring_expenses} mode={mode} />
      <WeekendVsWeekday weekend_vs_weekday={weekend_vs_weekday} mode={mode} {...chartProps} />
      <TopGrowingCategories top_growing_categories={top_growing_categories} mode={mode} />

      {income_insights && incomeEnabled && (
        <IncomeInsightsSection data={income_insights} {...chartProps} />
      )}
    </div>
  );
}
