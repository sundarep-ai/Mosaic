import { CATEGORY_ICONS } from "../../constants/categories";
import { useCurrency } from "../../CurrencyContext";

export default function AlertBanners({ recurring_alerts, category_trend_alerts, mode }) {
  const { fmt } = useCurrency();
  const isSolo = mode === "solo";

  return (
    <section className="space-y-3">
      {recurring_alerts.map((a, i) => {
        const prevDisplay = a.my_previous_avg != null ? a.my_previous_avg : a.previous_avg;
        const currDisplay = a.my_current_amount != null ? a.my_current_amount : a.current_amount;

        return (
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
                {fmt(prevDisplay)}
                <span className="font-normal text-on-surface-variant"> to </span>
                {fmt(currDisplay)}
              </p>
              <p className="text-xs text-on-surface-variant mt-0.5">
                Recurring payment &middot; {a.category}
                {!isSolo && a.my_previous_avg != null && a.my_previous_avg !== a.previous_avg && (
                  <span> &middot; Full: {fmt(a.previous_avg)} &rarr; {fmt(a.current_amount)}</span>
                )}
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
        );
      })}

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
              {!isSolo && a.shared_current_month_amount != null && a.shared_current_month_amount !== a.current_month_amount && (
                <span> &middot; Shared: {fmt(a.shared_current_month_amount)}</span>
              )}
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
  );
}
