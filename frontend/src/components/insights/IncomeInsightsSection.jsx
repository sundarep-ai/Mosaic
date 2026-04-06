import {
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  CartesianGrid,
  ComposedChart,
  Area,
} from "recharts";
import { useCurrency } from "../../CurrencyContext";
import EmptyState from "./EmptyState";

export default function IncomeInsightsSection({ data, CHART_COLORS, isDark, tooltipStyle, tooltipItemStyle, tooltipLabelStyle }) {
  const { fmt } = useCurrency();

  if (!data) return null;

  const { savings_rate, income_vs_expense, income_by_source } = data;

  const currentSavings = savings_rate?.current_month;
  const savingsTrend = savings_rate?.trend || [];
  const monthlyComparison = income_vs_expense?.monthly || [];
  const currentBySource = income_by_source?.current_month || [];

  const hasData = savingsTrend.some(s => s.income > 0) || currentSavings?.income > 0;

  if (!hasData) {
    return (
      <section>
        <h2 className="font-headline text-xl font-bold mb-6 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">account_balance</span>
          Income Insights
        </h2>
        <EmptyState icon="account_balance" message="Add income entries to see income insights" />
      </section>
    );
  }

  const isPositiveSavings = (currentSavings?.rate_pct || 0) >= 0;

  return (
    <section className="space-y-8">
      <h2 className="font-headline text-xl font-bold flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">account_balance</span>
        Income Insights
      </h2>

      {/* Row 1: Savings rate card + Income by source */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        {/* Savings Rate Card */}
        <div className={`md:col-span-4 p-8 rounded-[2rem] relative overflow-hidden ${
          isPositiveSavings ? "bg-primary text-on-primary" : "bg-error text-on-error"
        }`}>
          <span className={`font-label text-xs uppercase tracking-[0.2em] font-bold ${
            isPositiveSavings ? "text-on-primary/70" : "text-on-error/70"
          }`}>
            Savings Rate
          </span>
          <div className="mt-4 font-headline text-4xl font-extrabold">
            {currentSavings?.rate_pct || 0}%
          </div>
          <div className="mt-4 space-y-2 text-sm opacity-80">
            <div className="flex justify-between">
              <span>Income</span>
              <span className="font-bold">{fmt(currentSavings?.income || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span>Expenses</span>
              <span className="font-bold">{fmt(currentSavings?.expenses || 0)}</span>
            </div>
            <div className="flex justify-between pt-2 border-t border-current/20">
              <span>Net savings</span>
              <span className="font-bold">{fmt(currentSavings?.savings || 0)}</span>
            </div>
          </div>
          <div className={`absolute top-0 right-0 w-48 h-48 blur-[80px] rounded-full -mr-16 -mt-16 ${
            isPositiveSavings ? "bg-on-primary/10" : "bg-on-error/10"
          }`} />
        </div>

        {/* Income by Source */}
        <div className="md:col-span-8 bg-surface-container p-8 rounded-[2rem]">
          <h3 className="font-headline text-lg font-bold mb-6">Income by Source</h3>
          {currentBySource.length > 0 && currentBySource.some(s => s.amount > 0) ? (
            <ResponsiveContainer width="100%" height={Math.max(120, currentBySource.filter(s => s.amount > 0).length * 50)}>
              <BarChart
                data={currentBySource.filter(s => s.amount > 0).map(s => ({
                  name: s.source,
                  amount: s.amount,
                }))}
                layout="vertical"
                margin={{ top: 0, right: 20, left: 10, bottom: 0 }}
              >
                <XAxis type="number" hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={140}
                  tick={{ fontSize: 12, fontWeight: 600, fill: isDark ? "#bec8c8" : "#2f3334" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  formatter={(val) => [fmt(val), "Amount"]}
                  contentStyle={tooltipStyle}
                  itemStyle={tooltipItemStyle}
                  labelStyle={tooltipLabelStyle}
                />
                <Bar dataKey="amount" name="Amount" fill={CHART_COLORS[0]} radius={[0, 8, 8, 0]} barSize={20} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-on-surface-variant text-sm text-center py-8">No income this month</p>
          )}
        </div>
      </div>

      {/* Row 2: Income vs Expense trend */}
      {monthlyComparison.length > 0 && monthlyComparison.some(m => m.income > 0 || m.expense > 0) && (
        <div className="bg-surface-container p-8 rounded-[2rem]">
          <h3 className="font-headline text-lg font-bold mb-6">Income vs Expenses</h3>
          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart
              data={monthlyComparison.map(m => ({
                month: m.month.slice(5),
                Income: m.income,
                Expenses: m.expense,
                Surplus: m.surplus,
              }))}
              margin={{ top: 10, right: 20, left: 10, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={isDark ? "#3a3e3e" : "#e0e3e3"} />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 12, fontWeight: 600, fill: isDark ? "#bec8c8" : "#2f3334" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 12, fill: isDark ? "#bec8c8" : "#2f3334" }}
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
              <Bar dataKey="Income" fill={CHART_COLORS[0]} radius={[8, 8, 0, 0]} barSize={24} />
              <Bar dataKey="Expenses" fill={CHART_COLORS[1]} radius={[8, 8, 0, 0]} barSize={24} />
              <Line
                type="monotone"
                dataKey="Surplus"
                stroke={CHART_COLORS[2]}
                strokeWidth={2}
                dot={{ r: 4, fill: CHART_COLORS[2] }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Row 3: Savings rate trend */}
      {savingsTrend.length > 0 && savingsTrend.some(s => s.income > 0) && (
        <div className="bg-surface-container p-8 rounded-[2rem]">
          <h3 className="font-headline text-lg font-bold mb-6">Savings Rate Trend</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart
              data={savingsTrend.map(s => ({
                month: s.month.slice(5),
                "Savings Rate": s.rate_pct,
              }))}
              margin={{ top: 10, right: 20, left: 10, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={isDark ? "#3a3e3e" : "#e0e3e3"} />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 12, fontWeight: 600, fill: isDark ? "#bec8c8" : "#2f3334" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 12, fill: isDark ? "#bec8c8" : "#2f3334" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip
                formatter={(val) => [`${val}%`, "Savings Rate"]}
                contentStyle={tooltipStyle}
                itemStyle={tooltipItemStyle}
                labelStyle={tooltipLabelStyle}
              />
              <Line
                type="monotone"
                dataKey="Savings Rate"
                stroke={CHART_COLORS[0]}
                strokeWidth={2.5}
                dot={{ r: 4, fill: CHART_COLORS[0] }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
