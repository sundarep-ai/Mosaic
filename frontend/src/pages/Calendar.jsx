import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { getExpenses } from "../api/expenses";
import { useCurrency } from "../CurrencyContext";
import { useUsers } from "../ConfigContext";
import { useAuth } from "../auth/AuthContext";
import { calcMyPortion } from "../utils/portion";

const DAYS_OF_WEEK = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const MONTH_NAMES_SHORT = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

const MIN_YEAR = 2000;
const MAX_YEAR = 2099;

const pad = (n) => String(n).padStart(2, "0");

export default function Calendar() {
  const navigate = useNavigate();
  const { fmt } = useCurrency();
  const { userA, userB, mode } = useUsers();
  const { user } = useAuth();
  const me = user?.displayName || userA;
  const other = me === userA ? userB : userA;
  const isSolo = mode === "solo";
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerYear, setPickerYear] = useState(year);
  const pickerRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    async function fetchMonth() {
      setLoading(true);
      setError(null);
      try {
        const startDate = `${year}-${pad(month + 1)}-01`;
        const lastDay = new Date(year, month + 1, 0).getDate();
        const endDate = `${year}-${pad(month + 1)}-${pad(lastDay)}`;
        const data = await getExpenses({ start_date: startDate, end_date: endDate, sort: "asc" });
        if (!cancelled) setExpenses(data);
      } catch {
        if (!cancelled) setError("Could not load expenses. Is the server running?");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchMonth();
    return () => { cancelled = true; };
  }, [year, month]);

  // Aggregate daily portions (user's share) and shared totals
  // Exclude Payment and Reimbursement from calendar display
  const dailyTotals = {};
  let monthTotal = 0;
  let monthSharedTotal = 0;
  let monthCount = 0;
  for (const e of expenses) {
    if (e.category === "Payment" || e.category === "Reimbursement") continue;
    const portion = calcMyPortion(e, me, other);
    dailyTotals[e.date] = (dailyTotals[e.date] || 0) + portion;
    monthTotal += portion;
    if (e.split_method !== "Personal") monthSharedTotal += e.amount;
    monthCount++;
  }

  // Calendar grid
  const firstDayOfWeek = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const totalCells = Math.ceil((firstDayOfWeek + daysInMonth) / 7) * 7;
  const cells = [];
  for (let i = 0; i < totalCells; i++) {
    const day = i - firstDayOfWeek + 1;
    cells.push(day >= 1 && day <= daysInMonth ? day : null);
  }

  const goToPrev = () => {
    if (month === 0) { setYear(year - 1); setMonth(11); }
    else setMonth(month - 1);
  };
  const goToNext = () => {
    if (month === 11) { setYear(year + 1); setMonth(0); }
    else setMonth(month + 1);
  };

  const isToday = (day) =>
    day === today.getDate() && month === today.getMonth() && year === today.getFullYear();

  const handleDayClick = (day) => {
    const dateStr = `${year}-${pad(month + 1)}-${pad(day)}`;
    navigate("/history", { state: { start_date: dateStr, end_date: dateStr } });
  };

  // Close picker on outside click
  useEffect(() => {
    if (!pickerOpen) return;
    const handleClick = (e) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target)) {
        setPickerOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [pickerOpen]);

  const openPicker = () => {
    setPickerYear(year);
    setPickerOpen(true);
  };

  const selectMonth = (m) => {
    setYear(pickerYear);
    setMonth(m);
    setPickerOpen(false);
  };

  // Compute heat intensity using a log scale for graceful shading.
  // This prevents one large outlier from washing out all other days.
  const dailyValues = Object.values(dailyTotals).filter((v) => v > 0);
  const maxDaily = Math.max(0, ...dailyValues);
  const minDaily = dailyValues.length > 0 ? Math.min(...dailyValues) : 0;
  const useLogScale = maxDaily > 0 && maxDaily / Math.max(minDaily, 1) > 3;
  const logMax = useLogScale ? Math.log(maxDaily + 1) : 0;
  const logMin = useLogScale ? Math.log(minDaily + 1) : 0;
  const getIntensity = (amount) => {
    if (amount <= 0 || maxDaily <= 0) return 0;
    if (useLogScale) {
      const logVal = Math.log(amount + 1);
      const normalized = logMax > logMin ? (logVal - logMin) / (logMax - logMin) : 1;
      return 0.15 + normalized * 0.85;
    }
    return 0.15 + (amount / maxDaily) * 0.85;
  };

  return (
    <div className="space-y-10">
      {/* Header + Month Navigation */}
      <section className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="font-headline text-3xl font-bold tracking-tight text-on-surface">
            Calendar
          </h1>
          <p className="text-on-surface-variant font-medium">
            Daily spending at a glance.
          </p>
        </div>
        <div className="relative" ref={pickerRef}>
          <div className="bg-surface-container-high p-1.5 rounded-full flex items-center shadow-inner">
            <button
              onClick={goToPrev}
              className="w-10 h-10 rounded-full flex items-center justify-center hover:bg-surface-container-highest transition-colors active:scale-95 duration-200"
            >
              <span className="material-symbols-outlined">chevron_left</span>
            </button>
            <button
              onClick={openPicker}
              className="px-6 font-headline font-bold text-lg text-on-surface min-w-[200px] text-center hover:bg-surface-container-highest rounded-full py-2 transition-colors flex items-center justify-center gap-2"
            >
              {MONTH_NAMES[month]} {year}
              <span className="material-symbols-outlined text-[18px] text-on-surface-variant">
                {pickerOpen ? "expand_less" : "expand_more"}
              </span>
            </button>
            <button
              onClick={goToNext}
              className="w-10 h-10 rounded-full flex items-center justify-center hover:bg-surface-container-highest transition-colors active:scale-95 duration-200"
            >
              <span className="material-symbols-outlined">chevron_right</span>
            </button>
          </div>

          {/* Month/Year Picker Dropdown */}
          {pickerOpen && (
            <div className="absolute right-0 md:left-1/2 md:-translate-x-1/2 mt-3 w-[300px] bg-surface-container-lowest rounded-3xl shadow-xl shadow-on-surface/10 border border-outline-variant/20 p-5 z-50">
              {/* Year selector */}
              <div className="flex items-center justify-between mb-4">
                <button
                  onClick={() => setPickerYear((y) => Math.max(MIN_YEAR, y - 1))}
                  className="w-9 h-9 rounded-full flex items-center justify-center hover:bg-surface-container-high transition-colors active:scale-95 duration-200"
                >
                  <span className="material-symbols-outlined text-[20px]">chevron_left</span>
                </button>
                <span className="font-headline font-bold text-lg text-on-surface">{pickerYear}</span>
                <button
                  onClick={() => setPickerYear((y) => Math.min(MAX_YEAR, y + 1))}
                  className="w-9 h-9 rounded-full flex items-center justify-center hover:bg-surface-container-high transition-colors active:scale-95 duration-200"
                >
                  <span className="material-symbols-outlined text-[20px]">chevron_right</span>
                </button>
              </div>
              {/* Month grid */}
              <div className="grid grid-cols-3 gap-2">
                {MONTH_NAMES_SHORT.map((name, i) => {
                  const isSelected = i === month && pickerYear === year;
                  const isCurrent = i === today.getMonth() && pickerYear === today.getFullYear();
                  return (
                    <button
                      key={i}
                      onClick={() => selectMonth(i)}
                      className={`py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 active:scale-95
                        ${isSelected
                          ? "bg-primary text-on-primary shadow-sm font-bold"
                          : isCurrent
                            ? "ring-2 ring-primary text-primary font-bold hover:bg-surface-container-high"
                            : "text-on-surface hover:bg-surface-container-high"
                        }
                      `}
                    >
                      {name}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Monthly Aggregate */}
      <div className="bg-surface-container-lowest p-8 rounded-[2rem] flex flex-col sm:flex-row sm:items-center justify-between gap-4 relative overflow-hidden group">
        <div className="relative z-10">
          <span className="font-label text-xs uppercase tracking-[0.2em] text-on-surface-variant font-bold">
            Your Expense
          </span>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="font-headline text-5xl font-extrabold text-primary">
              {fmt(monthTotal)}
            </span>
          </div>
          {!isSolo && monthSharedTotal > 0 && (
            <p className="mt-2 text-sm font-medium">
              <span className="text-on-surface-variant">Total shared spend: </span>
              <span className="text-secondary font-bold">{fmt(monthSharedTotal)}</span>
            </p>
          )}
          <p className="mt-2 text-sm text-on-surface-variant font-medium">
            {monthCount} expense{monthCount !== 1 ? "s" : ""} in {MONTH_NAMES[month]}
          </p>
        </div>
        <div className="absolute -right-12 -bottom-12 w-48 h-48 bg-primary/5 rounded-full blur-3xl group-hover:scale-110 transition-transform duration-500"></div>
      </div>

      {/* Calendar Grid */}
      {error ? (
        <div className="flex items-center justify-center h-64 text-error text-sm">{error}</div>
      ) : loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : (
        <div className="bg-surface-container-lowest p-4 sm:p-6 rounded-[2rem]">
          {/* Day-of-week headers */}
          <div className="grid grid-cols-7 gap-1 sm:gap-2 mb-2">
            {DAYS_OF_WEEK.map((d) => (
              <div key={d} className="text-center font-label text-xs uppercase tracking-[0.15em] text-on-surface-variant font-bold py-2">
                {d}
              </div>
            ))}
          </div>
          {/* Day cells */}
          <div className="grid grid-cols-7 gap-1 sm:gap-2">
            {cells.map((day, i) => {
              if (day === null) {
                return <div key={i} className="min-h-[70px] sm:min-h-[90px]" />;
              }
              const dateKey = `${year}-${pad(month + 1)}-${pad(day)}`;
              const amount = dailyTotals[dateKey] || 0;
              const intensity = getIntensity(amount);
              return (
                <button
                  key={i}
                  onClick={() => handleDayClick(day)}
                  className={`min-h-[70px] sm:min-h-[90px] rounded-xl sm:rounded-2xl p-2 sm:p-3 flex flex-col justify-between text-left transition-colors duration-200 cursor-pointer relative overflow-hidden
                    ${isToday(day) ? "ring-2 ring-primary" : ""}
                    ${amount > 0 ? "hover:ring-2 hover:ring-primary/50" : "hover:bg-surface-container-high"}
                    bg-surface-container
                  `}
                >
                  {amount > 0 && (
                    <div
                      className="absolute inset-0 bg-primary rounded-xl sm:rounded-2xl pointer-events-none"
                      style={{ opacity: 0.05 + intensity * 0.2 }}
                    />
                  )}
                  <span className={`relative text-xs sm:text-sm font-bold ${isToday(day) ? "text-primary" : "text-on-surface"}`}>
                    {day}
                  </span>
                  {amount > 0 && (
                    <span className="relative text-primary font-bold text-[11px] sm:text-sm mt-auto">
                      {fmt(amount)}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
