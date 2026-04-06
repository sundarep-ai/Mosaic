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

function WeekendPanel({ data, title, fmt, isDark, CHART_COLORS, tooltipStyle, tooltipItemStyle, tooltipLabelStyle }) {
  const hasData = (data.weekday.count + data.weekend.count) > 0;

  if (!hasData) {
    return (
      <div className="flex-1">
        <h3 className="font-headline text-lg font-bold mb-4">{title}</h3>
        <EmptyState icon="calendar_month" message="No data" />
      </div>
    );
  }

  const catMap = {};
  for (const c of data.weekday.by_category) {
    catMap[c.category] = { weekday: c.amount, weekend: 0 };
  }
  for (const c of data.weekend.by_category) {
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

  return (
    <div className="flex-1 min-w-0">
      <h3 className="font-headline text-lg font-bold mb-4">{title}</h3>
      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-surface-container-lowest p-4 rounded-2xl">
          <span className="font-label text-xs uppercase tracking-[0.15em] text-on-surface-variant font-bold">
            Weekday
          </span>
          <div className="mt-1 font-headline text-2xl font-extrabold text-on-surface">
            {fmt(data.weekday.total)}
          </div>
          <p className="text-xs text-on-surface-variant mt-0.5">
            {data.weekday.count} expenses
          </p>
        </div>
        <div className="bg-surface-container-lowest p-4 rounded-2xl">
          <span className="font-label text-xs uppercase tracking-[0.15em] text-on-surface-variant font-bold">
            Weekend
          </span>
          <div className="mt-1 font-headline text-2xl font-extrabold text-on-surface">
            {fmt(data.weekend.total)}
          </div>
          <p className="text-xs text-on-surface-variant mt-0.5">
            {data.weekend.count} expenses
          </p>
        </div>
      </div>

      {(data.weekday.total + data.weekend.total) > 0 && (
        <div className="bg-surface-container p-3 rounded-2xl text-center mb-4">
          <p className="text-sm text-on-surface-variant">
            Weekend share:{" "}
            <span className="font-bold text-on-surface">
              {Math.round(
                (data.weekend.total / (data.weekday.total + data.weekend.total || 1)) * 100
              )}%
            </span>
          </p>
        </div>
      )}

      {chartData.length > 0 && (
        <div className="bg-surface-container p-4 rounded-2xl">
          <ResponsiveContainer width="100%" height={Math.max(160, chartData.length * 44)}>
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 0, right: 16, left: 8, bottom: 0 }}
            >
              <XAxis type="number" hide />
              <YAxis
                type="category"
                dataKey="name"
                width={80}
                tick={{ fontSize: 11, fontWeight: 600, fill: isDark ? "#bec8c8" : "#2f3334" }}
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
                wrapperStyle={{ fontSize: 11, paddingTop: 12, color: isDark ? "#bec8c8" : "#2f3334" }}
              />
              <Bar dataKey="weekday" name="Weekday" fill={CHART_COLORS[0]} radius={[0, 8, 8, 0]} barSize={14} />
              <Bar dataKey="weekend" name="Weekend" fill={CHART_COLORS[1]} radius={[0, 8, 8, 0]} barSize={14} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export default function WeekendVsWeekday({ weekend_vs_weekday, mode, CHART_COLORS, isDark, tooltipStyle, tooltipItemStyle, tooltipLabelStyle }) {
  const { fmt } = useCurrency();
  const isSolo = mode === "solo";

  const yourData = weekend_vs_weekday.your_expense || { weekday: { total: 0, count: 0, by_category: [] }, weekend: { total: 0, count: 0, by_category: [] } };
  const sharedData = weekend_vs_weekday.shared_expense || yourData;

  const hasAnyData = (yourData.weekday.count + yourData.weekend.count) > 0;

  const panelProps = { fmt, isDark, CHART_COLORS, tooltipStyle, tooltipItemStyle, tooltipLabelStyle };

  return (
    <section>
      <h2 className="font-headline text-xl font-bold mb-6 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">calendar_month</span>
        Weekend vs Weekday Spending
      </h2>
      {hasAnyData ? (
        <div className={`grid gap-6 ${isSolo ? "grid-cols-1" : "grid-cols-1 lg:grid-cols-2"}`}>
          <WeekendPanel data={yourData} title="Your Expense" {...panelProps} />
          {!isSolo && (
            <WeekendPanel data={sharedData} title="Shared Expense" {...panelProps} />
          )}
        </div>
      ) : (
        <EmptyState icon="calendar_month" message="No spending data available yet" />
      )}
    </section>
  );
}
