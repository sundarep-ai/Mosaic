import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { getBalance, getMonthlySummary, getExpenses, getPersonalSummary, getMyExpenseSummary } from "../api/expenses";
import { getMonthlyIncomeSummary } from "../api/income";
import { CATEGORY_ICONS, CATEGORY_BG } from "../constants/categories";
import { useUsers } from "../ConfigContext";
import { useCurrency } from "../CurrencyContext";
import { useDateFormat } from "../DateFormatContext";
import { useAuth } from "../auth/AuthContext";
import { useIncomeMode } from "../hooks/useIncomeMode";
import Avatar from "../components/Avatar";

export default function Landing() {
  const { userA, userB, mode } = useUsers();
  const { user } = useAuth();
  const me = user?.displayName || userA;
  const other = me === userA ? userB : userA;
  const isPersonal = mode === "personal";
  const isBlended = mode === "blended";
  const { fmt } = useCurrency();
  const { formatDate } = useDateFormat();
  const { incomeEnabled } = useIncomeMode();
  const [balance, setBalance] = useState(null);
  const [monthlySummary, setMonthlySummary] = useState([]);
  const [recentExpenses, setRecentExpenses] = useState([]);
  const [personalSpend, setPersonalSpend] = useState(null);
  const [myExpense, setMyExpense] = useState(null);
  const [monthlyIncome, setMonthlyIncome] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const promises = [
          isPersonal ? Promise.resolve({ amount: 0, description: "Personal mode" }) : getBalance(),
          getMonthlySummary(),
          getExpenses({ limit: 5, sort: "desc" }),
          getMyExpenseSummary(),
        ];
        if (isBlended) promises.push(getPersonalSummary());
        if (incomeEnabled) promises.push(getMonthlyIncomeSummary());

        const results = await Promise.all(promises);
        setBalance(results[0]);
        setMonthlySummary(results[1]);
        setRecentExpenses(results[2]);
        setMyExpense(results[3]);
        let idx = 4;
        if (isBlended && results[idx]) { setPersonalSpend(results[idx]); idx++; }
        if (incomeEnabled && results[idx]) setMonthlyIncome(results[idx]);
      } catch (err) {
        setError("Could not load dashboard data. Is the server running?");
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [isPersonal, isBlended, incomeEnabled]);

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

  const balanceAmount = balance?.amount ?? 0;
  const balanceText = balance?.description ?? "All settled up!";

  return (
    <div className="space-y-10">
      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="font-headline text-3xl font-extrabold text-on-surface tracking-tight mb-2">
            Home
          </h1>
          <p className="text-on-surface-variant font-medium">
            {isPersonal ? "Your personal financial overview at a glance." : "Your shared financial overview at a glance."}
          </p>
        </div>
        <Link
          to="/add"
          className="bg-gradient-to-br from-primary to-primary-dim text-on-primary px-8 py-4 rounded-full font-headline font-bold flex items-center gap-2 shadow-[0_4px_24px_rgba(16,106,106,0.2)] active:scale-95 transition-transform"
        >
          <span
            className="material-symbols-outlined"
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            add_circle
          </span>
          Add Expense
        </Link>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
        {/* Balance / Total Spend Card */}
        <div className={`${isPersonal && incomeEnabled ? "md:col-span-6" : "md:col-span-4"} bg-surface-container-lowest p-8 rounded-[2rem] flex flex-col justify-between relative overflow-hidden group`}>
          <div className="relative z-10">
            {isPersonal ? (
              <>
                <span className="font-label text-xs uppercase tracking-[0.2em] text-on-surface-variant font-bold">
                  Your Expense This Month
                </span>
                <div className="mt-4 flex items-baseline gap-2">
                  <span className="font-headline text-5xl font-extrabold text-primary">
                    {fmt(myExpense?.my_total ?? 0)}
                  </span>
                </div>
                <div className="mt-6 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary-container text-on-primary-container text-sm font-bold">
                  <span className="material-symbols-outlined text-[16px]">account_balance_wallet</span>
                  {monthlySummary.length} {monthlySummary.length === 1 ? "category" : "categories"}
                </div>
              </>
            ) : (
              <>
                <span className="font-label text-xs uppercase tracking-[0.2em] text-on-surface-variant font-bold">
                  Current Balance
                </span>
                <div className="mt-4 flex items-baseline gap-2">
                  <span className="font-headline text-5xl font-extrabold text-primary">
                    {Math.abs(balanceAmount) < 0.01 ? fmt(0) : fmt(Math.abs(balanceAmount))}
                  </span>
                </div>
                <div className="mt-6 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary-container text-on-primary-container text-sm font-bold">
                  <span className="material-symbols-outlined text-[16px]">
                    {balanceAmount > 0.01 ? "trending_up" : balanceAmount < -0.01 ? "trending_down" : "check_circle"}
                  </span>
                  {balanceText}
                </div>
              </>
            )}
          </div>

          {/* Settle button — hide in solo */}
          {!isPersonal && (
            <Link
              to="/add"
              state={{ description: "Payment", category: "Payment", split_method: "100% other" }}
              className="mt-8 inline-flex items-center gap-2 px-6 py-3 rounded-full bg-secondary-container text-on-secondary-container font-headline font-bold text-sm shadow-sm active:scale-95 transition-transform hover:shadow-md"
            >
              <span className="material-symbols-outlined text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                handshake
              </span>
              Settle
            </Link>
          )}

          <div className="absolute -right-12 -bottom-12 w-48 h-48 bg-primary/5 rounded-full blur-3xl group-hover:scale-110 transition-transform duration-500"></div>

          {/* Footer — avatars and subtitle */}
          <div className="mt-12 flex items-center gap-4 text-on-surface-variant">
            {isPersonal ? (
              <>
                <div className="w-10 h-10 rounded-full border-4 border-surface-container-lowest overflow-hidden">
                  <Avatar user={me} size="md" />
                </div>
                <p className="text-xs font-medium italic">Personal expense tracker</p>
              </>
            ) : (
              <>
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
              </>
            )}
          </div>
        </div>

        {/* Your Expense Card (duo/hybrid) */}
        {!isPersonal && myExpense && (
          <div className={`${incomeEnabled ? "md:col-span-4" : "md:col-span-4"} bg-surface-container p-8 rounded-[2rem]`}>
            <span className="font-label text-xs uppercase tracking-[0.2em] text-on-surface-variant font-bold">
              Your Expense This Month
            </span>
            <div className="mt-4">
              <span className="font-headline text-4xl font-extrabold text-secondary">
                {fmt(myExpense.my_total)}
              </span>
            </div>
          </div>
        )}

        {/* Income This Month tile */}
        {incomeEnabled && (
          <div className={`${isPersonal ? "md:col-span-6" : "md:col-span-4"} bg-surface-container p-8 rounded-[2rem] relative overflow-hidden group`}>
            <span className="font-label text-xs uppercase tracking-[0.2em] text-on-surface-variant font-bold">
              Income This Month
            </span>
            <div className="mt-4">
              <span className="font-headline text-4xl font-extrabold text-tertiary">
                {fmt(monthlyIncome?.total ?? 0)}
              </span>
            </div>
            <div className="mt-4 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-tertiary-container text-on-tertiary-container text-sm font-bold">
              <span className="material-symbols-outlined text-[16px]">payments</span>
              {monthlyIncome?.by_source?.length
                ? monthlyIncome.by_source.map((s) => s.source).join(", ")
                : "No income logged yet"}
            </div>
            <div className="absolute -right-12 -bottom-12 w-40 h-40 bg-tertiary/5 rounded-full blur-3xl group-hover:scale-110 transition-transform duration-500"></div>
          </div>
        )}

        {/* Quick Actions & Monthly Summary — full width when income enabled, otherwise same as before */}
        <div className={`${incomeEnabled ? "md:col-span-12" : isPersonal ? "md:col-span-8" : "md:col-span-4"} bg-surface-container p-8 rounded-[2rem]`}>
          <div className="flex items-center justify-between mb-8">
            <h3 className="font-headline text-xl font-bold">
              This Month&apos;s Spend by Category
            </h3>
          </div>

          {monthlySummary.length === 0 ? (
            <p className="text-on-surface-variant text-sm">
              No expenses this month yet.
            </p>
          ) : (
            <div className="space-y-5">
              {(() => {
                const top5 = monthlySummary.slice(0, 5);
                const maxAmount = Math.max(
                  ...top5.map((i) => i.amount),
                );
                return top5.map((item) => {
                const pct =
                  maxAmount > 0
                    ? Math.round((item.amount / maxAmount) * 100)
                    : 0;
                return (
                  <div key={item.category} className="flex items-center gap-4">
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center ${CATEGORY_BG[item.category] || CATEGORY_BG.Other}`}
                    >
                      <span className="material-symbols-outlined">
                        {CATEGORY_ICONS[item.category] || "more_horiz"}
                      </span>
                    </div>
                    <div className="flex-1">
                      <div className="flex justify-between text-sm mb-1.5">
                        <span className="font-bold">{item.category}</span>
                        <span className="text-on-surface-variant font-medium">
                          {fmt(item.amount)}
                        </span>
                      </div>
                      <div className="h-2 w-full bg-surface-container-high rounded-full">
                        <div
                          className="h-full bg-primary rounded-full transition-all duration-500"
                          style={{ width: `${pct}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                );
              });
              })()}
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div className="md:col-span-12 bg-surface-container-lowest p-8 rounded-[2rem]">
          <div className="flex items-center justify-between mb-8">
            <h3 className="font-headline text-2xl font-bold">
              Recent Activity
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

          {recentExpenses.length === 0 ? (
            <p className="text-on-surface-variant text-sm">
              No expenses recorded yet.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="text-on-surface-variant font-label text-xs uppercase tracking-widest border-b border-surface-container-high">
                    <th scope="col" className="pb-4 font-bold">Description</th>
                    <th scope="col" className="pb-4 font-bold">Category</th>
                    {!isPersonal && <th scope="col" className="pb-4 font-bold">Paid By</th>}
                    <th scope="col" className="pb-4 font-bold">Date</th>
                    <th scope="col" className="pb-4 font-bold text-right">Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-container-low">
                  {recentExpenses.map((expense) => (
                    <tr
                      key={expense.id}
                      className="group hover:bg-surface-container-low/50 transition-colors"
                    >
                      <td className="py-5 pr-4">
                        <div className="flex items-center gap-4">
                          <div
                            className={`w-10 h-10 rounded-2xl flex items-center justify-center ${CATEGORY_BG[expense.category] || CATEGORY_BG.Other}`}
                          >
                            <span className="material-symbols-outlined text-sm">
                              {CATEGORY_ICONS[expense.category] || "more_horiz"}
                            </span>
                          </div>
                          <p className="font-bold text-on-surface">
                            {expense.description}
                          </p>
                        </div>
                      </td>
                      <td className="py-5">
                        <span className="px-3 py-1 rounded-full bg-surface-container-high text-[11px] font-bold uppercase text-on-surface-variant">
                          {expense.category}
                        </span>
                      </td>
                      {!isPersonal && (
                        <td className="py-5">
                          <span className="text-sm font-medium">
                            {expense.paid_by}
                          </span>
                        </td>
                      )}
                      <td className="py-5">
                        <span className="text-sm text-on-surface-variant font-medium">
                          {formatDate(expense.date)}
                        </span>
                      </td>
                      <td className="py-5 text-right">
                        <span className="font-headline font-bold text-lg">
                          {fmt(expense.amount)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
