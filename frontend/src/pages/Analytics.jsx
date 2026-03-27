import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
} from "recharts";
import { getAnalytics, getExpenses } from "../api/expenses";
import { CATEGORY_ICONS } from "../constants/categories";
import { useUsers } from "../ConfigContext";

const CHART_COLORS = [
  "#106a6a",
  "#7a5a00",
  "#954b00",
  "#005d5d",
  "#6b4e00",
  "#834100",
  "#9eeae9",
  "#ffdfa0",
  "#ffa35d",
  "#777b7c",
];

const PRESETS = [
  { label: "1M", months: 1 },
  { label: "3M", months: 3 },
  { label: "6M", months: 6 },
  { label: "1Y", months: 12 },
];

function getDateRange(months) {
  const end = new Date();
  const start = new Date();
  start.setMonth(start.getMonth() - months);
  return {
    start_date: start.toISOString().split("T")[0],
    end_date: end.toISOString().split("T")[0],
  };
}

export default function Analytics() {
  const { userA, userB } = useUsers();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activePreset, setActivePreset] = useState("3M");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [dateParams, setDateParams] = useState(getDateRange(3));
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [drillDownData, setDrillDownData] = useState(null);
  const [drillDownLoading, setDrillDownLoading] = useState(false);

  const fetchData = async (params) => {
    setLoading(true);
    setError(null);
    try {
      const result = await getAnalytics(params);
      setData(result);
    } catch (err) {
      setError("Could not load analytics. Is the server running?");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(getDateRange(3));
  }, []);

  const handlePreset = (preset) => {
    setActivePreset(preset.label);
    setCustomStart("");
    setCustomEnd("");
    const params = getDateRange(preset.months);
    setDateParams(params);
    setSelectedCategory(null);
    setDrillDownData(null);
    fetchData(params);
  };

  const handleCustomRange = () => {
    if (customStart && customEnd) {
      setActivePreset("custom");
      const params = { start_date: customStart, end_date: customEnd };
      setDateParams(params);
      setSelectedCategory(null);
      setDrillDownData(null);
      fetchData(params);
    }
  };

  const fetchDrillDown = async (category) => {
    setDrillDownLoading(true);
    setSelectedCategory(category);
    try {
      const expenses = await getExpenses({
        category,
        ...dateParams,
      });
      const grouped = {};
      for (const e of expenses) {
        if (!grouped[e.description]) {
          grouped[e.description] = { description: e.description, amount: 0, count: 0 };
        }
        grouped[e.description].amount += e.amount;
        grouped[e.description].count += 1;
      }
      const sorted = Object.values(grouped)
        .sort((a, b) => b.amount - a.amount)
        .slice(0, 7);
      setDrillDownData(sorted);
    } finally {
      setDrillDownLoading(false);
    }
  };

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="flex items-center justify-center h-64 text-error text-sm">
        {error}
      </div>
    );
  }

  const totalSpend = data?.total_spend ?? 0;
  const totalShared = data?.total_shared_spend ?? 0;

  return (
    <div className="space-y-10">
      {/* Header + Date Filter */}
      <section className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="font-headline text-3xl font-bold tracking-tight text-on-surface">
            Spend Analytics
          </h1>
          <p className="text-on-surface-variant font-medium">
            Visualizing your collaborative growth.
          </p>
        </div>
        <div className="bg-surface-container-high p-1.5 rounded-full flex items-center shadow-inner flex-wrap">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() => handlePreset(p)}
              className={`px-6 py-2 rounded-full text-sm font-semibold transition-all ${
                activePreset === p.label
                  ? "bg-primary text-on-primary shadow-sm font-bold"
                  : "hover:bg-surface-container-highest"
              }`}
            >
              {p.label}
            </button>
          ))}
          <div className="h-4 w-[1px] bg-outline-variant/30 mx-2 hidden sm:block"></div>
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
              className="bg-transparent border-none focus:ring-0 text-sm px-2 py-1"
            />
            <span className="text-outline text-xs">to</span>
            <input
              type="date"
              value={customEnd}
              onChange={(e) => setCustomEnd(e.target.value)}
              className="bg-transparent border-none focus:ring-0 text-sm px-2 py-1"
            />
            <button
              onClick={handleCustomRange}
              className="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold hover:bg-surface-container-highest transition-all"
            >
              <span className="material-symbols-outlined text-[18px]">
                calendar_today
              </span>
              Apply
            </button>
          </div>
        </div>
      </section>

      {data && (
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
          {/* Total Spend Summary */}
          <div className="md:col-span-4 bg-surface-container-lowest p-8 rounded-[2rem] flex flex-col justify-between relative overflow-hidden group">
            <div className="relative z-10">
              <span className="font-label text-xs uppercase tracking-[0.2em] text-on-surface-variant font-bold">
                Total Shared Spend
              </span>
              <div className="mt-4 flex items-baseline gap-2">
                <span className="font-headline text-5xl font-extrabold text-primary">
                  ${totalShared.toFixed(2)}
                </span>
              </div>
              <div className="mt-3 text-sm text-on-surface-variant font-medium">
                Total spend: ${totalSpend.toFixed(2)}
              </div>
            </div>
            <div className="absolute -right-12 -bottom-12 w-48 h-48 bg-primary/5 rounded-full blur-3xl group-hover:scale-110 transition-transform duration-500"></div>
            <div className="mt-12 flex items-center gap-4 text-on-surface-variant">
              <div className="flex -space-x-3">
                <div className="w-10 h-10 rounded-full border-4 border-surface-container-lowest bg-primary-container flex items-center justify-center">
                  <span className="material-symbols-outlined text-sm text-on-primary-container">
                    person
                  </span>
                </div>
                <div className="w-10 h-10 rounded-full border-4 border-surface-container-lowest bg-secondary-container flex items-center justify-center">
                  <span className="material-symbols-outlined text-sm text-on-secondary-container">
                    person
                  </span>
                </div>
              </div>
              <p className="text-xs font-medium italic">
                Shared between {userA} & {userB}
              </p>
            </div>
          </div>

          {/* Category Distribution / Drill-Down */}
          <div className="md:col-span-8 bg-surface-container p-8 rounded-[2rem]">
            <div className="flex items-center justify-between mb-8">
              {selectedCategory ? (
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => {
                      setSelectedCategory(null);
                      setDrillDownData(null);
                    }}
                    className="w-10 h-10 rounded-full bg-surface-container-high flex items-center justify-center hover:bg-surface-container-highest transition-colors"
                  >
                    <span className="material-symbols-outlined">arrow_back</span>
                  </button>
                  <div>
                    <h3 className="font-headline text-xl font-bold">
                      {selectedCategory}
                    </h3>
                    <p className="text-on-surface-variant text-sm font-medium">
                      Top spending by description
                    </p>
                  </div>
                </div>
              ) : (
                <h3 className="font-headline text-xl font-bold">
                  Category Distribution
                </h3>
              )}
            </div>
            {selectedCategory ? (
              drillDownLoading ? (
                <div className="flex items-center justify-center h-[280px]">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                </div>
              ) : drillDownData && drillDownData.length > 0 ? (
                <ResponsiveContainer width="100%" height={Math.max(200, drillDownData.length * 44)}>
                  <BarChart
                    data={drillDownData.map((e) => ({
                      name:
                        e.description.length > 25
                          ? e.description.substring(0, 22) + "..."
                          : e.description,
                      fullName: e.description,
                      amount: e.amount,
                      count: e.count,
                    }))}
                    layout="vertical"
                    margin={{ top: 0, right: 20, left: 10, bottom: 0 }}
                  >
                    <XAxis type="number" hide />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={140}
                      tick={{ fontSize: 12, fontWeight: 600 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      formatter={(val, name, props) => {
                        const d = props.payload;
                        return [`$${val.toFixed(2)} (${d.count} expense${d.count !== 1 ? "s" : ""})`, "Total"];
                      }}
                      labelFormatter={(label, payload) => {
                        if (payload && payload[0]) {
                          return payload[0].payload.fullName;
                        }
                        return label;
                      }}
                      contentStyle={{
                        borderRadius: "1rem",
                        border: "none",
                        boxShadow: "0 4px 24px rgba(47,51,52,0.1)",
                        fontFamily: "Public Sans",
                      }}
                    />
                    <Bar
                      dataKey="amount"
                      fill={CHART_COLORS[0]}
                      radius={[0, 8, 8, 0]}
                      barSize={28}
                      label={({ x, y, width, height, value, index }) => {
                        const text = `$${value.toFixed(2)}`;
                        const inside = width > text.length * 7 + 16;
                        return (
                          <text
                            x={inside ? x + width - 8 : x + width + 6}
                            y={y + height / 2}
                            fill={inside ? "white" : CHART_COLORS[index % CHART_COLORS.length]}
                            textAnchor={inside ? "end" : "start"}
                            dominantBaseline="central"
                            fontSize={11}
                            fontWeight={700}
                          >
                            {text}
                          </text>
                        );
                      }}
                    >
                      {drillDownData.map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-on-surface-variant text-sm text-center py-12">
                  No expenses found in this category
                </p>
              )
            ) : data.distribution?.length > 0 ? (
              (() => {
                const top7 = data.distribution.slice(0, 7);
                const rest = data.distribution.slice(7);
                const pieData = rest.length > 0
                  ? [
                      ...top7,
                      {
                        category: "Others (sum)",
                        amount: rest.reduce((s, e) => s + e.amount, 0),
                        percentage: Math.round(rest.reduce((s, e) => s + e.percentage, 0) * 10) / 10,
                      },
                    ]
                  : top7;
                return (
                  <>
                    <ResponsiveContainer width="100%" height={280}>
                      <PieChart>
                        <Pie
                          data={pieData}
                          dataKey="amount"
                          nameKey="category"
                          cx="50%"
                          cy="50%"
                          outerRadius={100}
                          innerRadius={50}
                          label={({ category, percentage }) =>
                            `${category} ${percentage}%`
                          }
                          labelLine={{ stroke: "#afb2b3" }}
                          style={{ fontWeight: 700, cursor: "pointer" }}
                          onClick={(entry) => {
                            if (entry.category !== "Others (sum)") {
                              fetchDrillDown(entry.category);
                            }
                          }}
                        >
                          {pieData.map((entry, i) => (
                            <Cell
                              key={entry.category}
                              fill={CHART_COLORS[i % CHART_COLORS.length]}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(val) => [`$${val.toFixed(2)}`, "Amount"]}
                          contentStyle={{
                            borderRadius: "1rem",
                            border: "none",
                            boxShadow: "0 4px 24px rgba(47,51,52,0.1)",
                            fontFamily: "Public Sans",
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                    <p className="text-center text-xs text-on-surface-variant mt-2">
                      Click a category to see top expenses
                    </p>
                  </>
                );
              })()
            ) : (
              <p className="text-on-surface-variant text-sm text-center py-12">
                No data available
              </p>
            )}
          </div>

          {/* Payer Breakdown */}
          <div className="md:col-span-5 bg-surface-container-lowest p-8 rounded-[2rem]">
            <h3 className="font-headline text-xl font-bold mb-2">
              Payer Breakdown
            </h3>
            <p className="text-on-surface-variant text-sm font-medium mb-8">
              Who's picking up the tab
            </p>
            {data.by_payer?.length > 0 ? (
              <div className="space-y-6">
                {data.by_payer.map((p, i) => {
                  const pct =
                    totalSpend > 0
                      ? Math.round((p.amount / totalSpend) * 100)
                      : 0;
                  const colors = [
                    {
                      bar: "bg-primary",
                      bg: "bg-primary-container",
                      text: "text-primary",
                    },
                    {
                      bar: "bg-secondary",
                      bg: "bg-secondary-container",
                      text: "text-secondary",
                    },
                  ];
                  const c = colors[i % colors.length];
                  return (
                    <div key={p.payer}>
                      <div className="flex items-center gap-4 mb-3">
                        <div
                          className={`w-10 h-10 rounded-xl flex items-center justify-center ${c.bg} ${c.text}`}
                        >
                          <span className="material-symbols-outlined">
                            person
                          </span>
                        </div>
                        <div className="flex-1">
                          <div className="flex justify-between text-sm mb-1">
                            <span className="font-bold">{p.payer}</span>
                            <span className="text-on-surface-variant font-medium">
                              ${p.amount.toFixed(2)} · {pct}%
                            </span>
                          </div>
                          <div className="h-2 w-full bg-surface-container-high rounded-full">
                            <div
                              className={`h-full ${c.bar} rounded-full transition-all duration-500`}
                              style={{ width: `${pct}%` }}
                            ></div>
                          </div>
                        </div>
                      </div>
                      <p className="text-xs text-on-surface-variant ml-14">
                        {p.count} expense{p.count !== 1 ? "s" : ""}
                      </p>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-on-surface-variant text-sm text-center py-12">
                No data available
              </p>
            )}
          </div>

          {/* Spending Velocity Chart */}
          <div className="md:col-span-7 bg-primary text-on-primary p-8 rounded-[2rem] overflow-hidden relative">
            <div className="relative z-10">
              <h3 className="font-headline text-xl font-bold mb-2">
                Spending Velocity
              </h3>
              <p className="text-on-primary/70 text-sm font-medium">
                Monthly spending trend
              </p>
            </div>
            <div className="mt-8 relative z-10">
              {data.over_time?.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={data.over_time}>
                    <XAxis
                      dataKey="month"
                      tick={{ fontSize: 11, fill: "rgba(224,255,254,0.6)" }}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(val) => {
                        const [y, m] = val.split("-");
                        return new Date(y, m - 1).toLocaleDateString("en-US", { month: "short", year: "numeric" });
                      }}
                    />
                    <YAxis hide />
                    <Tooltip
                      formatter={(val, name, props) => [
                        `$${val.toFixed(2)} (${props.payload.count} expense${props.payload.count !== 1 ? "s" : ""})`,
                        "Spend",
                      ]}
                      labelFormatter={(label) => {
                        const [y, m] = label.split("-");
                        return new Date(y, m - 1).toLocaleDateString("en-US", { month: "short", year: "numeric" });
                      }}
                      contentStyle={{
                        borderRadius: "1rem",
                        border: "none",
                        boxShadow: "0 4px 24px rgba(0,0,0,0.2)",
                        fontFamily: "Public Sans",
                        background: "#fff",
                        color: "#2f3334",
                      }}
                      itemStyle={{ color: "#2f3334" }}
                    />
                    <Line
                      type="monotone"
                      dataKey="amount"
                      stroke="white"
                      strokeWidth={3}
                      dot={{ fill: "white", r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-on-primary/60 text-sm text-center py-12">
                  No trend data available
                </p>
              )}
            </div>
            <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 blur-[80px] rounded-full -mr-20 -mt-20"></div>
          </div>

          {/* Top Expenses Table */}
          <div className="md:col-span-12 bg-surface-container-lowest p-8 rounded-[2rem]">
            <div className="flex items-center justify-between mb-8">
              <h3 className="font-headline text-2xl font-bold">
                Largest Outlays
              </h3>
              <Link
                to="/history"
                className="text-primary font-bold text-sm flex items-center gap-1 hover:underline"
              >
                View All History
                <span className="material-symbols-outlined text-[18px]">
                  chevron_right
                </span>
              </Link>
            </div>
            {data.top_expenses?.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="text-on-surface-variant font-label text-xs uppercase tracking-widest border-b border-surface-container-high">
                      <th scope="col" className="pb-4 font-bold">Expense Detail</th>
                      <th scope="col" className="pb-4 font-bold">Category</th>
                      <th scope="col" className="pb-4 font-bold">Paid By</th>
                      <th scope="col" className="pb-4 font-bold">Date</th>
                      <th scope="col" className="pb-4 font-bold text-right">Amount</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-container-low">
                    {data.top_expenses.map((e) => (
                      <tr
                        key={e.id}
                        className="group hover:bg-surface-container-low/50 transition-colors"
                      >
                        <td className="py-6 pr-4">
                          <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-2xl bg-surface-container flex items-center justify-center text-on-surface">
                              <span className="material-symbols-outlined">
                                {CATEGORY_ICONS[e.category] || "more_horiz"}
                              </span>
                            </div>
                            <div>
                              <p className="font-bold text-on-surface">
                                {e.description}
                              </p>
                              <p className="text-xs text-on-surface-variant font-medium">
                                {e.split_method || "Shared"}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="py-6">
                          <span className="px-3 py-1 rounded-full bg-surface-container-high text-[11px] font-bold uppercase text-on-surface-variant">
                            {e.category}
                          </span>
                        </td>
                        <td className="py-6">
                          <div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center">
                              <span className="material-symbols-outlined text-on-primary text-[10px]">
                                person
                              </span>
                            </div>
                            <span className="text-sm font-medium">
                              {e.paid_by}
                            </span>
                          </div>
                        </td>
                        <td className="py-6">
                          <span className="text-sm text-on-surface-variant font-medium">
                            {e.date}
                          </span>
                        </td>
                        <td className="py-6 text-right">
                          <span className="font-headline font-bold text-lg">
                            ${e.amount.toFixed(2)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-on-surface-variant text-sm text-center py-8">
                No expenses in this range
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
