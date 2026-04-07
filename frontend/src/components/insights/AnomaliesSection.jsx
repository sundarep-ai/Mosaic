import { CATEGORY_ICONS } from "../../constants/categories";
import { useCurrency } from "../../CurrencyContext";
import { useDateFormat } from "../../DateFormatContext";

export default function AnomaliesSection({ anomalies, mode }) {
  const { fmt } = useCurrency();
  const { formatDate } = useDateFormat();
  const isSolo = mode === "solo";

  if (anomalies.length === 0) return null;

  return (
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
            <p className="text-2xl font-headline font-extrabold mt-1">
              {fmt(a.my_portion != null ? a.my_portion : a.amount)}
            </p>
            {!isSolo && a.my_portion != null && a.my_portion !== a.amount && (
              <p className="text-xs text-on-surface-variant mt-0.5">
                Full amount: {fmt(a.amount)}
              </p>
            )}
            <p className="text-xs text-on-surface-variant mt-2">
              {a.category} avg: {fmt(a.category_mean)} &middot; {formatDate(a.date)}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
