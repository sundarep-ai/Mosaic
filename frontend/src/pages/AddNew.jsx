import { useSearchParams } from "react-router-dom";
import { useIncomeMode } from "../hooks/useIncomeMode";
import AddExpense from "./AddExpense";
import AddIncome from "./AddIncome";

export default function AddNew() {
  const { incomeEnabled } = useIncomeMode();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab =
    searchParams.get("tab") === "income" && incomeEnabled ? "income" : "expense";

  if (!incomeEnabled) {
    return <AddExpense />;
  }

  return (
    <div>
      <div className="max-w-2xl mx-auto px-4 mb-6">
        <div className="bg-surface-container-high p-1.5 rounded-2xl flex gap-1.5 h-14">
          <button
            type="button"
            onClick={() => setSearchParams({})}
            className={`flex-1 rounded-xl flex items-center justify-center gap-2 transition-colors ${
              tab === "expense"
                ? "bg-surface-container-lowest shadow-sm font-bold text-primary border-2 border-primary/10"
                : "font-semibold text-on-surface-variant hover:bg-surface-container"
            }`}
          >
            <span
              className="material-symbols-outlined text-[18px]"
              style={
                tab === "expense"
                  ? { fontVariationSettings: "'FILL' 1" }
                  : undefined
              }
            >
              receipt_long
            </span>
            Expense
          </button>
          <button
            type="button"
            onClick={() => setSearchParams({ tab: "income" })}
            className={`flex-1 rounded-xl flex items-center justify-center gap-2 transition-colors ${
              tab === "income"
                ? "bg-surface-container-lowest shadow-sm font-bold text-tertiary border-2 border-tertiary/10"
                : "font-semibold text-on-surface-variant hover:bg-surface-container"
            }`}
          >
            <span
              className="material-symbols-outlined text-[18px]"
              style={
                tab === "income"
                  ? { fontVariationSettings: "'FILL' 1" }
                  : undefined
              }
            >
              payments
            </span>
            Income
          </button>
        </div>
      </div>

      {tab === "expense" ? <AddExpense /> : <AddIncome />}
    </div>
  );
}
