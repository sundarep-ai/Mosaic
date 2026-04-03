import { useState, useEffect } from "react";
import {
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from "recharts";
import { getInsights } from "../api/expenses";
import { CATEGORY_ICONS } from "../constants/categories";
import { useTheme } from "../ThemeContext";
import { useCurrency } from "../CurrencyContext";

const CHART_COLORS_LIGHT = [
  "#106a6a", "#7a5a00", "#954b00", "#005d5d", "#6b4e00",
  "#834100", "#9eeae9", "#ffdfa0", "#ffa35d", "#777b7c",
];
const CHART_COLORS_DARK = [
  "#7ad4d3", "#e5c36c", "#ffb77c", "#5ec5c4", "#c8aa50",
  "#e69b5a", "#a0f0ef", "#ffd580", "#ffcba4", "#a8b5b4",
];

const FREQ_COLORS = {
  Weekly: "bg-error-container text-on-error-container",
  Biweekly: "bg-tertiary-container text-on-tertiary-container",
  Monthly: "bg-primary-container text-on-primary-container",
  Quarterly: "bg-secondary-container text-on-secondary-container",
  Annual: "bg-surface-container-highest text-on-surface-variant",
};

export default function Insights() {
  const { theme } = useTheme();
  const { fmt } = useCurrency();
  const isDark = theme === "dark";
  const CHART_COLORS = isDark ? CHART_COLORS_DARK : CHART_COLORS_LIGHT;
  const tooltipTextColor = isDark ? "#e0e3e3" : "#2f3334";
  const tooltipStyle = {
    borderRadius: "1rem",
    border: "none",
    boxShadow: isDark ? "0 4px 24px rgba(0,0,0,0.4)" : "0 4px 24px rgba(47,51,52,0.1)",
    fontFamily: "Public Sans",
    background: isDark ? "#282c2c" : "#fff",
    color: tooltipTextColor,
  };
  const tooltipItemStyle = { color: tooltipTextColor };
  const tooltipLabelStyle = { color: tooltipTextColor };

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

  const {
    recurring_expenses = [],
    recurring_alerts = [],
    weekend_vs_weekday = { weekday: { total: 0, count: 0, by_category: [] }, weekend: { total: 0, count: 0, by_category: [] } },
    category_trend_alerts = [],
    anomalies = [],
    forecast = { recurring_total: 0, variable_total: 0, total_forecast: 0, last_month_total: 0, change_vs_last_month_pct: 0, by_category: [] },
    top_growing_categories = [],
  } = data || {};

  const hasAlerts = recurring_alerts.length > 0 || category_trend_alerts.length > 0;

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

      {/* ── Alert Banners ───────────────────────────────────────── */}
      {hasAlerts && (
        <section className="space-y-3">
          {recurring_alerts.map((a, i) => (
            <div
              key={`ra-${i}`}
              className="flex items-center gap-4 bg-tertiary-container/60 border border-tertiary/20 p-4 rounded-2xl"
            >
              <div className="w-10 h-10 rounded-xl bg-tertiary/15 flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined text-tertiary">
                  {a.direction === "up" ? "trending_up" : "trending_down"}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-on-surface">
                  {a.description}
                  <span className="font-normal text-on-surface-variant"> changed from </span>
                  {fmt(a.previous_avg)}
                  <span className="font-normal text-on-surface-variant"> to </span>
                  {fmt(a.current_amount)}
                </p>
                <p className="text-xs text-on-surface-variant mt-0.5">
                  Recurring payment · {a.category}
                </p>
              </div>
              <span
                className={`px-3 py-1 rounded-full text-xs font-bold shrink-0 ${
                  a.direction === "up"
                    ? "bg-error-container text-on-error-container"
                    : "bg-primary-container text-on-primary-container"
                }`}
              >
                {a.direction === "up" ? "+" : ""}{a.change_pct}%
              </span>
            </div>
          ))}

          {category_trend_alerts.map((a, i) => (
            <div
              key={`ct-${i}`}
              className={`flex items-center gap-4 p-4 rounded-2xl border ${
                a.direction === "up"
                  ? "bg-error-container/40 border-error/15"
                  : "bg-primary-container/40 border-primary/15"
              }`}
            >
              <div
                className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                  a.direction === "up" ? "bg-error/15" : "bg-primary/15"
                }`}
              >
                <span className={`material-symbols-outlined ${a.direction === "up" ? "text-error" : "text-primary"}`}>
                  {CATEGORY_ICONS[a.category] || "category"}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-on-surface">
                  {a.category}
                  <span className="font-normal text-on-surface-variant">
                    {" "}is {a.direction === "up" ? "up" : "down"} this month
                  </span>
                </p>
                <p className="text-xs text-on-surface-variant mt-0.5">
                  {fmt(a.current_month_amount)} vs {fmt(a.three_month_avg)} 3-month avg
                </p>
              </div>
              <span
                className={`px-3 py-1 rounded-full text-xs font-bold shrink-0 ${
                  a.direction === "up"
                    ? "bg-error-container text-on-error-container"
                    : "bg-primary-container text-on-primary-container"
                }`}
              >
                {a.direction === "up" ? "+" : ""}{a.change_pct}%
              </span>
            </div>
          ))}
        </section>
      )}

      {/* ── Forecast ────────────────────────────────────────────── */}
      <section>
        {(() => {
          const now = new Date();
          const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1);
          const forecastMonthLabel = nextMonth.toLocaleString("default", { month: "long", year: "numeric" });
          return (
            <h2 className="font-headline text-xl font-bold mb-6 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">auto_awesome</span>
              {forecastMonthLabel} Forecast
            </h2>
          );
        })()}
        {forecast.total_forecast > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
            {/* Summary card */}
            <div className="md:col-span-4 bg-primary text-on-primary p-8 rounded-[2rem] relative overflow-hidden">
              <span className="font-label text-xs uppercase tracking-[0.2em] text-on-primary/70 font-bold">
                Estimated Total
              </span>
              <div className="mt-4 font-headline text-4xl font-extrabold">
                {fmt(forecast.total_forecast)}
              </div>
              <div className="mt-4 space-y-2 text-sm text-on-primary/80">
                <div className="flex justify-between">
                  <span>Recurring</span>
                  <span className="font-bold">{fmt(forecast.recurring_total)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Variable</span>
                  <span className="font-bold">{fmt(forecast.variable_total)}</span>
                </div>
              </div>
              {forecast.last_month_total > 0 && (
                <div className="mt-6 pt-4 border-t border-on-primary/20">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="material-symbols-outlined text-[18px]">
                      {forecast.change_vs_last_month_pct >= 0 ? "trending_up" : "trending_down"}
                    </span>
                    <span>
                      {forecast.change_vs_last_month_pct >= 0 ? "+" : ""}
                      {forecast.change_vs_last_month_pct}% vs last month ({fmt(forecast.last_month_total)})
                    </span>
                  </div>
                </div>
              )}
              <div className="absolute top-0 right-0 w-48 h-48 bg-on-primary/10 blur-[80px] rounded-full -mr-16 -mt-16" />
            </div>

            {/* Per-category breakdown chart */}
            <div className="md:col-span-8 bg-surface-container p-8 rounded-[2rem]">
              <h3 className="font-headline text-lg font-bold mb-6">By Category</h3>
              {forecast.by_category.length > 0 ? (
                <ResponsiveContainer width="100%" height={Math.max(200, forecast.by_category.slice(0, 8).length * 44)}>
                  <BarChart
                    data={forecast.by_category.slice(0, 8).map((c) => ({
                      name: c.category.length > 18 ? c.category.slice(0, 15) + "..." : c.category,
                      forecast: c.forecast,
                      last_month: c.last_month,
                    }))}
                    layout="vertical"
                    margin={{ top: 0, right: 20, left: 10, bottom: 0 }}
                  >
                    <XAxis type="number" hide />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={110}
                      tick={{ fontSize: 12, fontWeight: 600, fill: isDark ? "#bec8c8" : "#2f3334" }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      formatter={(val, name) => [fmt(val), name]}
                      contentStyle={tooltipStyle}
                      itemStyle={tooltipItemStyle}
                      labelStyle={tooltipLabelStyle}
                    />
                    <Legend
                      wrapperStyle={{ fontSize: 12, paddingTop: 16, color: isDark ? "#bec8c8" : "#2f3334" }}
                    />
                    <Bar dataKey="forecast" name="Forecast" fill={CHART_COLORS[0]} radius={[0, 8, 8, 0]} barSize={16} />
                    <Bar dataKey="last_month" name="Last Month" fill={CHART_COLORS[1]} radius={[0, 8, 8, 0]} barSize={16} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-on-surface-variant text-sm text-center py-8">No category data</p>
              )}
            </div>
          </div>
        ) : (
          <EmptyState icon="auto_awesome" message="Need at least 1 month of history for forecasting" />
        )}
      </section>

      {/* ── Anomalies ───────────────────────────────────────────── */}
      {anomalies.length > 0 && (
        <section>
          <h2 className="font-headline text-xl font-bold mb-6 flex items-center gap-2">
            <span className="material-symbols-outlined text-error">warning</span>
            Unusual Expenses
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {anomalies.slice(0, 6).map((a) => (
              <div
                key={a.id}
                className="bg-surface-container-lowest p-6 rounded-2xl border border-surface-container-high"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-xl bg-error-container flex items-center justify-center">
                    <span className="material-symbols-outlined text-on-error-container">
                      {CATEGORY_ICONS[a.category] || "receipt_long"}
                    </span>
                  </div>
                  <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                    a.direction === "high"
                      ? "bg-error-container text-on-error-container"
                      : "bg-primary-container text-on-primary-container"
                  }`}>
                    {a.direction === "high" ? "Unusually High" : "Unusually Low"}
                  </span>
                </div>
                <p className="font-bold text-on-surface truncate">{a.description}</p>
                <p className="text-2xl font-headline font-extrabold mt-1">{fmt(a.amount)}</p>
                <p className="text-xs text-on-surface-variant mt-2">
                  {a.category} avg: {fmt(a.category_mean)} · {a.date}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Recurring Expenses ──────────────────────────────────── */}
      <section>
        <h2 className="font-headline text-xl font-bold mb-6 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">autorenew</span>
          Recurring Expenses
        </h2>
        {recurring_expenses.length > 0 ? (
          <div className="bg-surface-container-lowest rounded-[2rem] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="text-on-surface-variant font-label text-xs uppercase tracking-widest border-b border-surface-container-high">
                    <th scope="col" className="px-6 py-4 font-bold">Expense</th>
                    <th scope="col" className="px-6 py-4 font-bold">Category</th>
                    <th scope="col" className="px-6 py-4 font-bold">Frequency</th>
                    <th scope="col" className="px-6 py-4 font-bold text-right">Avg Amount</th>
                    <th scope="col" className="px-6 py-4 font-bold text-right">Last Amount</th>
                    <th scope="col" className="px-6 py-4 font-bold text-right">Occurrences</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-container-low">
                  {[...recurring_expenses].sort((a, b) => b.occurrence_count - a.occurrence_count).map((r, i) => (
                    <tr key={i} className="hover:bg-surface-container-low/50 transition-colors">
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-xl bg-surface-container flex items-center justify-center">
                            <span className="material-symbols-outlined text-on-surface">
                              {CATEGORY_ICONS[r.category] || "receipt_long"}
                            </span>
                          </div>
                          <span className="font-bold text-on-surface">{r.description}</span>
                        </div>
                      </td>
                      <td className="px-6 py-5">
                        <span className="px-3 py-1 rounded-full bg-surface-container-high text-[11px] font-bold uppercase text-on-surface-variant">
                          {r.category}
                        </span>
                      </td>
                      <td className="px-6 py-5">
                        <span className={`px-3 py-1 rounded-full text-xs font-bold ${FREQ_COLORS[r.frequency] || FREQ_COLORS.Monthly}`}>
                          {r.frequency}
                        </span>
                      </td>
                      <td className="px-6 py-5 text-right font-medium">{fmt(r.avg_amount)}</td>
                      <td className="px-6 py-5 text-right font-headline font-bold">{fmt(r.last_amount)}</td>
                      <td className="px-6 py-5 text-right text-on-surface-variant">{r.occurrence_count}x</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <EmptyState icon="autorenew" message="No recurring patterns detected yet. Keep logging expenses!" />
        )}
      </section>

      {/* ── Weekend vs Weekday ──────────────────────────────────── */}
      <section>
        <h2 className="font-headline text-xl font-bold mb-6 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">calendar_month</span>
          Weekend vs Weekday Spending
        </h2>
        {(weekend_vs_weekday.weekday.count + weekend_vs_weekday.weekend.count) > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
            {/* Summary cards */}
            <div className="md:col-span-4 space-y-4">
              <div className="bg-surface-container-lowest p-6 rounded-2xl">
                <span className="font-label text-xs uppercase tracking-[0.15em] text-on-surface-variant font-bold">
                  Weekday
                </span>
                <div className="mt-2 font-headline text-3xl font-extrabold text-on-surface">
                  {fmt(weekend_vs_weekday.weekday.total)}
                </div>
                <p className="text-sm text-on-surface-variant mt-1">
                  {weekend_vs_weekday.weekday.count} expenses
                </p>
              </div>
              <div className="bg-surface-container-lowest p-6 rounded-2xl">
                <span className="font-label text-xs uppercase tracking-[0.15em] text-on-surface-variant font-bold">
                  Weekend
                </span>
                <div className="mt-2 font-headline text-3xl font-extrabold text-on-surface">
                  {fmt(weekend_vs_weekday.weekend.total)}
                </div>
                <p className="text-sm text-on-surface-variant mt-1">
                  {weekend_vs_weekday.weekend.count} expenses
                </p>
              </div>
              {(weekend_vs_weekday.weekday.count + weekend_vs_weekday.weekend.count) > 0 && (
                <div className="bg-surface-container p-4 rounded-2xl text-center">
                  <p className="text-sm text-on-surface-variant">
                    Weekend share:{" "}
                    <span className="font-bold text-on-surface">
                      {Math.round(
                        (weekend_vs_weekday.weekend.total /
                          (weekend_vs_weekday.weekday.total + weekend_vs_weekday.weekend.total || 1)) * 100
                      )}%
                    </span>
                  </p>
                </div>
              )}
            </div>

            {/* Category breakdown chart */}
            <div className="md:col-span-8 bg-surface-container p-8 rounded-[2rem]">
              <h3 className="font-headline text-lg font-bold mb-6">Top Categories</h3>
              {(() => {
                // Merge weekday + weekend top categories for side-by-side comparison
                const catMap = {};
                for (const c of weekend_vs_weekday.weekday.by_category) {
                  catMap[c.category] = { weekday: c.amount, weekend: 0 };
                }
                for (const c of weekend_vs_weekday.weekend.by_category) {
                  if (!catMap[c.category]) catMap[c.category] = { weekday: 0, weekend: 0 };
                  catMap[c.category].weekend = c.amount;
                }
                const chartData = Object.entries(catMap)
                  .map(([category, vals]) => ({
                    name: category.length > 14 ? category.slice(0, 11) + "..." : category,
                    fullName: category,
                    weekday: vals.weekday,
                    weekend: vals.weekend,
                  }))
                  .sort((a, b) => (b.weekday + b.weekend) - (a.weekday + a.weekend))
                  .slice(0, 8);

                return chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={Math.max(200, chartData.length * 50)}>
                    <BarChart
                      data={chartData}
                      layout="vertical"
                      margin={{ top: 0, right: 20, left: 10, bottom: 0 }}
                    >
                      <XAxis type="number" hide />
                      <YAxis
                        type="category"
                        dataKey="name"
                        width={100}
                        tick={{ fontSize: 12, fontWeight: 600, fill: isDark ? "#bec8c8" : "#2f3334" }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        formatter={(val, name) => [fmt(val), name]}
                        labelFormatter={(_, payload) => payload?.[0]?.payload?.fullName || ""}
                        contentStyle={tooltipStyle}
                        itemStyle={tooltipItemStyle}
                        labelStyle={tooltipLabelStyle}
                      />
                      <Legend
                        wrapperStyle={{ fontSize: 12, paddingTop: 16, color: isDark ? "#bec8c8" : "#2f3334" }}
                      />
                      <Bar dataKey="weekday" name="Weekday" fill={CHART_COLORS[0]} radius={[0, 8, 8, 0]} barSize={18} />
                      <Bar dataKey="weekend" name="Weekend" fill={CHART_COLORS[1]} radius={[0, 8, 8, 0]} barSize={18} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-on-surface-variant text-sm text-center py-8">No category data</p>
                );
              })()}
            </div>
          </div>
        ) : (
          <EmptyState icon="calendar_month" message="No spending data available yet" />
        )}
      </section>

      {/* ── Top Growing Categories ──────────────────────────────── */}
      <section>
        <h2 className="font-headline text-xl font-bold mb-6 flex items-center gap-2">
          <span className="material-symbols-outlined text-error">trending_up</span>
          Top Growing Categories
        </h2>
        {top_growing_categories.length > 0 ? (
          <div className="bg-surface-container-lowest rounded-[2rem] p-8">
            <div className="space-y-4">
              {top_growing_categories.map((g, i) => {
                const isPositive = g.avg_mom_growth_pct > 0;
                return (
                  <div key={i} className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-surface-container flex items-center justify-center shrink-0">
                      <span className="material-symbols-outlined text-on-surface">
                        {CATEGORY_ICONS[g.category] || "category"}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-on-surface">{g.category}</span>
                        <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                          isPositive
                            ? "bg-error-container text-on-error-container"
                            : "bg-primary-container text-on-primary-container"
                        }`}>
                          {isPositive ? "+" : ""}{g.avg_mom_growth_pct}% / mo
                        </span>
                      </div>
                      <div className="flex gap-2 text-xs text-on-surface-variant">
                        {g.last_3_months.map((val, mi) => (
                          <span key={mi}>
                            {g.months?.[mi]?.slice(5) || `M${mi + 1}`}: {fmt(val)}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <EmptyState icon="trending_up" message="Need at least 2 months of data to detect trends" />
        )}
      </section>
    </div>
  );
}

function EmptyState({ icon, message }) {
  return (
    <div className="bg-surface-container-lowest rounded-[2rem] p-12 text-center">
      <span className="material-symbols-outlined text-4xl text-on-surface-variant/40 mb-4 block">
        {icon}
      </span>
      <p className="text-on-surface-variant text-sm font-medium">{message}</p>
    </div>
  );
}
