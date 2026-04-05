import { CATEGORY_ICONS } from "../../constants/categories";
import { useCurrency } from "../../CurrencyContext";
import EmptyState from "./EmptyState";

const FREQ_COLORS = {
  Weekly: "bg-error-container text-on-error-container",
  Biweekly: "bg-tertiary-container text-on-tertiary-container",
  Monthly: "bg-primary-container text-on-primary-container",
  Quarterly: "bg-secondary-container text-on-secondary-container",
  Annual: "bg-surface-container-highest text-on-surface-variant",
};

export default function RecurringExpenses({ recurring_expenses }) {
  const { fmt } = useCurrency();

  return (
    <section>
      <h2 className="font-headline text-xl font-bold mb-6 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">autorenew</span>
        Recurring Expenses
      </h2>
      {recurring_expenses.length > 0 ? (
        <div className="bg-surface-container-lowest rounded-[2rem] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-on-surface-variant font-label text-xs uppercase tracking-widest border-b border-surface-container-high">
                  <th scope="col" className="px-6 py-4 font-bold">Expense</th>
                  <th scope="col" className="px-6 py-4 font-bold">Category</th>
                  <th scope="col" className="px-6 py-4 font-bold">Frequency</th>
                  <th scope="col" className="px-6 py-4 font-bold text-right">Avg Amount</th>
                  <th scope="col" className="px-6 py-4 font-bold text-right">Last Amount</th>
                  <th scope="col" className="px-6 py-4 font-bold text-right">Occurrences</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-container-low">
                {[...recurring_expenses].sort((a, b) => b.occurrence_count - a.occurrence_count).map((r, i) => (
                  <tr key={i} className="hover:bg-surface-container-low/50 transition-colors">
                    <td className="px-6 py-5">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-surface-container flex items-center justify-center">
                          <span className="material-symbols-outlined text-on-surface">
                            {CATEGORY_ICONS[r.category] || "receipt_long"}
                          </span>
                        </div>
                        <span className="font-bold text-on-surface">{r.description}</span>
                      </div>
                    </td>
                    <td className="px-6 py-5">
                      <span className="px-3 py-1 rounded-full bg-surface-container-high text-[11px] font-bold uppercase text-on-surface-variant">
                        {r.category}
                      </span>
                    </td>
                    <td className="px-6 py-5">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${FREQ_COLORS[r.frequency] || FREQ_COLORS.Monthly}`}>
                        {r.frequency}
                      </span>
                    </td>
                    <td className="px-6 py-5 text-right font-medium">{fmt(r.avg_amount)}</td>
                    <td className="px-6 py-5 text-right font-headline font-bold">{fmt(r.last_amount)}</td>
                    <td className="px-6 py-5 text-right text-on-surface-variant">{r.occurrence_count}x</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <EmptyState icon="autorenew" message="No recurring patterns detected yet. Keep logging expenses!" />
      )}
    </section>
  );
}
