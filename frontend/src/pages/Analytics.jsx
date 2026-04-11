import { useState, useEffect, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
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
  Sankey,
  Layer,
  Rectangle,
} from "recharts";
import { getAnalytics, getExpenses } from "../api/expenses";
import { getIncomeSankey } from "../api/income";
import { CATEGORY_ICONS } from "../constants/categories";
import { useUsers } from "../ConfigContext";
import { useTheme } from "../ThemeContext";
import { useCurrency } from "../CurrencyContext";
import { useAuth } from "../auth/AuthContext";
import { useDateFormat } from "../DateFormatContext";
import { useIncomeMode } from "../hooks/useIncomeMode";
import DateInput from "../components/DateInput";
import Avatar from "../components/Avatar";
import { getDateRange, groupByDescription, groupByMonth } from "../utils/analytics";
import { getChartColors, getTooltipStyles } from "../utils/chartConfig";
import { buildSankeyData, SankeyNode } from "../components/SankeyChart";

const PRESETS = [
  { label: "1M", days: 30 },
  { label: "3M", days: 91 },
  { label: "6M", days: 182 },
  { label: "YTD", special: "ytd" },
  { label: "1Y", days: 365 },
  { label: "All", special: "all" },
];

// ---------------------------------------------------------------------------
// Analytics component
// ---------------------------------------------------------------------------

export default function Analytics() {
  const { userA, userB, mode } = useUsers();
  const { user } = useAuth();
  const me = user?.displayName || userA;
  const other = me === userA ? userB : userA;
  const isPersonal = mode === "personal";
  const isBlended = mode === "blended";
  const { theme } = useTheme();
  const { fmt } = useCurrency();
  const { formatDate } = useDateFormat();
  const navigate = useNavigate();
  const { incomeEnabled } = useIncomeMode();
  const isDark = theme === "dark";
  const CHART_COLORS = getChartColors(isDark);
  const { tooltipStyle, tooltipItemStyle, tooltipLabelStyle } = getTooltipStyles(isDark);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activePreset, setActivePreset] = useState("3M");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [dateParams, setDateParams] = useState(getDateRange(91));
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [drillDownData, setDrillDownData] = useState(null);
  const [drillDownLoading, setDrillDownLoading] = useState(false);
  const [categoryVelocityData, setCategoryVelocityData] = useState(null);
  const [sankeyData, setSankeyData] = useState(null);

  const fetchData = useCallback(async (params) => {
    setLoading(true);
    setError(null);
    try {
      const promises = [getAnalytics(params)];
      if (incomeEnabled) promises.push(getIncomeSankey(params));
      const [result, ...rest] = await Promise.all(promises);
      const sankeyResp = rest[0] ?? null;
      setData(result);
      if (sankeyResp) {
        setSankeyData(buildSankeyData(sankeyResp));
      } else {
        setSankeyData(null);
      }
    } catch (err) {
      setError("Could not load analytics. Is the server running?");
    } finally {
      setLoading(false);
    }
  }, [incomeEnabled]);

  useEffect(() => {
    fetchData(getDateRange(91));
  }, [fetchData]);

  const handlePreset = (preset) => {
    setActivePreset(preset.label);
    setCustomStart("");
    setCustomEnd("");
    let params;
    if (preset.special === "all") {
      params = {};
    } else if (preset.special === "ytd") {
      const now = new Date();
      params = {
        start_date: `${now.getFullYear()}-01-01`,
        end_date: now.toISOString().split("T")[0],
      };
    } else {
      params = getDateRange(preset.days);
    }
    setDateParams(params);
    setSelectedCategory(null);
    setDrillDownData(null);
    setCategoryVelocityData(null);
    fetchData(params);
  };

  const handleCustomRange = () => {
    if (customStart && customEnd) {
      setActivePreset("custom");
      const params = { start_date: customStart, end_date: customEnd };
      setDateParams(params);
      setSelectedCategory(null);
      setDrillDownData(null);
      setCategoryVelocityData(null);
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

      setDrillDownData(groupByDescription(expenses));
      setCategoryVelocityData(groupByMonth(expenses));
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
  const myShare = data?.my_share ?? 0;

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
            <DateInput
              value={customStart}
              onChange={(iso) => setCustomStart(iso)}
              className="bg-transparent border-none focus:ring-0 text-sm px-2 py-1 w-28"
            />
            <span className="text-outline text-xs">to</span>
            <DateInput
              value={customEnd}
              onChange={(iso) => setCustomEnd(iso)}
              className="bg-transparent border-none focus:ring-0 text-sm px-2 py-1 w-28"
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

          {/* Income → Expenses Sankey chart */}
          {incomeEnabled && (
            <div className="md:col-span-12 bg-surface-container p-8 rounded-[2rem]">
              <div className="flex items-center gap-3 mb-2">
                <span className="material-symbols-outlined text-tertiary" style={{ fontVariationSettings: "'FILL' 1" }}>
                  account_tree
                </span>
                <h3 className="font-headline text-xl font-bold">Income Flow</h3>
              </div>
              <p className="text-on-surface-variant text-sm font-medium mb-8">
                Where your money comes from and where it goes
              </p>
              {sankeyData ? (
                <ResponsiveContainer width="100%" height={460}>
                  <Sankey
                    data={sankeyData}
                    nodePadding={20}
                    nodeWidth={14}
                    margin={{ top: 10, right: 160, bottom: 10, left: 160 }}
                    link={{ stroke: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)", strokeWidth: 1 }}
                    node={
                      <SankeyNode
                        sourceCount={sankeyData.sourceCount}
                        isDark={isDark}
                        chartColors={CHART_COLORS}
                      />
                    }
                  >
                    <Tooltip
                      formatter={(val) => [fmt(val), "Amount"]}
                      contentStyle={tooltipStyle}
                      itemStyle={tooltipItemStyle}
                      labelStyle={tooltipLabelStyle}
                    />
                  </Sankey>
                </ResponsiveContainer>
              ) : (
                <div className="flex flex-col items-center justify-center h-40 text-on-surface-variant gap-3">
                  <span className="material-symbols-outlined text-4xl opacity-30">payments</span>
                  <p className="text-sm">No income logged for this period.</p>
                  <Link
                    to="/add-income"
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-tertiary-container text-on-tertiary-container text-sm font-bold"
                  >
                    <span className="material-symbols-outlined text-[16px]">add</span>
                    Log income
                  </Link>
                </div>
              )}
            </div>
          )}

          {/* Total Spend Summary */}
          <div className="md:col-span-4 bg-surface-container-lowest p-8 rounded-[2rem] flex flex-col justify-between relative overflow-hidden group">
            <div className="relative z-10">
              <span className="font-label text-xs uppercase tracking-[0.2em] text-on-surface-variant font-bold">
                Your Expense
              </span>
              <div className="mt-4 flex items-baseline gap-2">
                <span className="font-headline text-5xl font-extrabold text-primary">
                  {fmt(myShare)}
                </span>
              </div>
              {!isPersonal && (
                <div className="mt-3">
                  <div className="text-sm text-on-surface-variant font-medium">
                    Total shared spend: {fmt(totalShared)}
                  </div>
                </div>
              )}
            </div>
            <div className="absolute -right-12 -bottom-12 w-48 h-48 bg-primary/5 rounded-full blur-3xl group-hover:scale-110 transition-transform duration-500"></div>
            {!isPersonal && (
              <div className="mt-12 flex items-center gap-4 text-on-surface-variant">
                <div className="flex -space-x-3">
                  <div className="w-10 h-10 rounded-full border-4 border-surface-container-lowest overflow-hidden">
                    <Avatar user={me} size="md" />
                  </div>
                  <div className="w-10 h-10 rounded-full border-4 border-surface-container-lowest overflow-hidden">
                    <Avatar user={other} size="md" />
                  </div>
                </div>
                <p className="text-xs font-medium italic">
                  {isBlended ? `Blended with ${other}` : `Shared between ${me} & ${other}`}
                </p>
              </div>
            )}
            {isPersonal && (
              <div className="mt-12 flex items-center gap-4 text-on-surface-variant">
                <div className="w-10 h-10 rounded-full border-4 border-surface-container-lowest overflow-hidden">
                  <Avatar user={me} size="md" />
                </div>
                <p className="text-xs font-medium italic">Personal expense tracker</p>
              </div>
            )}
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
                      setCategoryVelocityData(null);
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
                      tick={{ fontSize: 12, fontWeight: 600, fill: isDark ? "#bec8c8" : "#2f3334" }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      formatter={(val, name, props) => {
                        const d = props.payload;
                        return [`${fmt(val)} (${d.count} expense${d.count !== 1 ? "s" : ""})`, "Total"];
                      }}
                      labelFormatter={(label, payload) => {
                        if (payload && payload[0]) {
                          return payload[0].payload.fullName;
                        }
                        return label;
                      }}
                      contentStyle={tooltipStyle}
                      itemStyle={tooltipItemStyle}
                      labelStyle={tooltipLabelStyle}
                    />
                    <Bar
                      dataKey="amount"
                      fill={CHART_COLORS[0]}
                      radius={[0, 8, 8, 0]}
                      barSize={28}
                      label={({ x, y, width, height, value, index }) => {
                        const text = fmt(value);
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
                          label={({ cx, cy, midAngle, outerRadius, category, percentage }) => {
                            const RADIAN = Math.PI / 180;
                            const radius = outerRadius + 20;
                            const x = cx + radius * Math.cos(-midAngle * RADIAN);
                            const y = cy + radius * Math.sin(-midAngle * RADIAN);
                            return (
                              <text
                                x={x}
                                y={y}
                                textAnchor={x > cx ? "start" : "end"}
                                dominantBaseline="central"
                                fill={isDark ? "#e0e3e3" : "#2f3334"}
                                style={{ fontWeight: 700, fontSize: 12 }}
                              >
                                {`${category} ${percentage}%`}
                              </text>
                            );
                          }}
                          labelLine={{ stroke: isDark ? "#889392" : "#afb2b3" }}
                          style={{ cursor: "pointer" }}
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
                          formatter={(val) => [fmt(val), "Amount"]}
                          contentStyle={tooltipStyle}
                          itemStyle={tooltipItemStyle}
                          labelStyle={tooltipLabelStyle}
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

          {/* Spending Velocity Chart */}
          <div className="md:col-span-12 bg-primary text-on-primary p-8 rounded-[2rem] overflow-hidden relative">
            <div className="relative z-10">
              <h3 className="font-headline text-xl font-bold mb-2">
                Spending Velocity
              </h3>
              <p className="text-on-primary/70 text-sm font-medium">
                {selectedCategory ? `${selectedCategory} — monthly trend` : "Monthly spending trend"}
              </p>
            </div>
            <div className="mt-8 relative z-10">
              {(categoryVelocityData ?? data.over_time)?.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart
                    data={categoryVelocityData ?? data.over_time}
                    onClick={(chartData) => {
                      if (!chartData?.activePayload?.[0]) return;
                      const month = chartData.activePayload[0].payload.month;
                      const [y, m] = month.split("-");
                      navigate("/history", {
                        state: {
                          month,
                          start_date: `${y}-${m}-01`,
                          end_date: new Date(y, m, 0).toISOString().split("T")[0],
                          ...(selectedCategory ? { category: selectedCategory } : {}),
                        },
                      });
                    }}
                    style={{ cursor: "pointer" }}
                  >
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
                        `${fmt(val)} (${props.payload.count} expense${props.payload.count !== 1 ? "s" : ""})`,
                        "Spend",
                      ]}
                      labelFormatter={(label) => {
                        const [y, m] = label.split("-");
                        return new Date(y, m - 1).toLocaleDateString("en-US", { month: "short", year: "numeric" });
                      }}
                      contentStyle={tooltipStyle}
                      itemStyle={tooltipItemStyle}
                      labelStyle={tooltipLabelStyle}
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
                  {selectedCategory ? `No trend data for ${selectedCategory}` : "No trend data available"}
                </p>
              )}
            </div>
            <div className="absolute top-0 right-0 w-64 h-64 bg-on-primary/10 blur-[80px] rounded-full -mr-20 -mt-20"></div>
          </div>

          {/* Payer Breakdown */}
          {!isPersonal && (
            <div className={`${isBlended ? "md:col-span-6" : "md:col-span-12"} bg-surface-container-lowest p-8 rounded-[2rem]`}>
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
                          <div className="w-10 h-10 rounded-xl overflow-hidden">
                            <Avatar user={p.payer} size="md" />
                          </div>
                          <div className="flex-1">
                            <div className="flex justify-between text-sm mb-1">
                              <span className="font-bold">{p.payer}</span>
                              <span className="text-on-surface-variant font-medium">
                                {fmt(p.amount)} · {pct}%
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
          )}

          {/* Personal vs Shared (blended only) */}
          {isBlended && data.by_split_type && (
            <div className="md:col-span-6 bg-surface-container-lowest p-8 rounded-[2rem]">
              <h3 className="font-headline text-xl font-bold mb-2">Personal vs Shared</h3>
              <p className="text-on-surface-variant text-sm font-medium mb-8">How your spending breaks down</p>
              <div className="space-y-6">
                {data.by_split_type.map((item) => {
                  const pct = totalSpend > 0 ? Math.round((item.amount / totalSpend) * 100) : 0;
                  const isShared = item.type === "Shared";
                  return (
                    <div key={item.type}>
                      <div className="flex justify-between text-sm mb-2">
                        <div className="flex items-center gap-2">
                          <span className="material-symbols-outlined text-[18px]">
                            {isShared ? "group" : "person"}
                          </span>
                          <span className="font-bold">{item.type}</span>
                        </div>
                        <span className="text-on-surface-variant font-medium">
                          {fmt(item.amount)} · {pct}%
                        </span>
                      </div>
                      <div className="h-2 w-full bg-surface-container-high rounded-full">
                        <div
                          className={`h-full ${isShared ? "bg-primary" : "bg-secondary"} rounded-full transition-all duration-500`}
                          style={{ width: `${pct}%` }}
                        ></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

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
                            <Avatar user={e.paid_by} size="sm" />
                            <span className="text-sm font-medium">
                              {e.paid_by}
                            </span>
                          </div>
                        </td>
                        <td className="py-6">
                          <span className="text-sm text-on-surface-variant font-medium">
                            {formatDate(e.date)}
                          </span>
                        </td>
                        <td className="py-6 text-right">
                          <span className="font-headline font-bold text-lg">
                            {fmt(e.amount)}
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
