import { CATEGORY_ICONS } from "../../constants/categories";
import { useCurrency } from "../../CurrencyContext";
import EmptyState from "./EmptyState";

export default function TopGrowingCategories({ top_growing_categories, mode }) {
  const { fmt } = useCurrency();
  const isPersonal = mode === "personal";

  return (
    <section>
      <h2 className="font-headline text-xl font-bold mb-6 flex items-center gap-2">
        <span className="material-symbols-outlined text-error">trending_up</span>
        Top Growing Categories
      </h2>
      {top_growing_categories.length > 0 ? (
        <div className="bg-surface-container-lowest rounded-[2rem] p-8">
          <div className="space-y-4">
            {top_growing_categories.map((g, i) => {
              const isPositive = g.avg_mom_growth_pct > 0;
              const showShared = !isPersonal && g.shared_last_3_months;
              return (
                <div key={i} className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-surface-container flex items-center justify-center shrink-0">
                    <span className="material-symbols-outlined text-on-surface">
                      {CATEGORY_ICONS[g.category] || "category"}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-on-surface">{g.category}</span>
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                        isPositive
                          ? "bg-error-container text-on-error-container"
                          : "bg-primary-container text-on-primary-container"
                      }`}>
                        {isPositive ? "+" : ""}{g.avg_mom_growth_pct}% / mo
                      </span>
                    </div>
                    <div className="flex gap-2 text-xs text-on-surface-variant">
                      {g.last_3_months.map((val, mi) => (
                        <span key={mi}>
                          {g.months?.[mi]?.slice(5) || `M${mi + 1}`}: {fmt(val)}
                          {showShared && g.shared_last_3_months[mi] !== val && (
                            <span className="text-on-surface-variant/60"> ({fmt(g.shared_last_3_months[mi])})</span>
                          )}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <EmptyState icon="trending_up" message="Need at least 2 months of data to detect trends" />
      )}
    </section>
  );
}
