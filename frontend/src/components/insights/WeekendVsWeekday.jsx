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

export default function WeekendVsWeekday({ weekend_vs_weekday, CHART_COLORS, isDark, tooltipStyle, tooltipItemStyle, tooltipLabelStyle }) {
  const { fmt } = useCurrency();

  return (
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
  );
}
