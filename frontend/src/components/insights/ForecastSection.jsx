import {
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";
import { useCurrency } from "../../CurrencyContext";
import EmptyState from "./EmptyState";

export default function ForecastSection({ forecast, CHART_COLORS, isDark, tooltipStyle, tooltipItemStyle, tooltipLabelStyle }) {
  const { fmt } = useCurrency();

  const now = new Date();
  const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1);
  const forecastMonthLabel = nextMonth.toLocaleString("default", { month: "long", year: "numeric" });

  return (
    <section>
      <h2 className="font-headline text-xl font-bold mb-6 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">auto_awesome</span>
        {forecastMonthLabel} Forecast
      </h2>
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
  );
}
