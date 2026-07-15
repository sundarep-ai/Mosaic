import { useState, useEffect, useCallback, useRef } from "react";
import { Link, useNavigate, useLocation, useSearchParams } from "react-router-dom";
import { useCurrency } from "../CurrencyContext";
import { useDateFormat } from "../DateFormatContext";
import { useToast } from "../ToastContext";
import {
  getExpenses,
  deleteExpense,
  exportExpenses,
  getSimilarDescriptions,
} from "../api/expenses";
import { CATEGORIES, CATEGORY_ICONS, CATEGORY_BG } from "../constants/categories";
import { useUsers } from "../ConfigContext";
import Avatar from "../components/Avatar";
import MergeDescriptionsModal from "../components/MergeDescriptionsModal";
import {
  buildExpenseParams,
  filtersToSearchParams,
  filtersFromSearchParams,
} from "../utils/expenseFilters";

const PAGE_SIZE = 100;

function getSplitBadge(method) {
  if (method === "50/50") {
    return (
      <span className="bg-secondary-container text-on-secondary-container px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border border-secondary/10 flex items-center gap-1">
        <span className="material-symbols-outlined text-xs">group</span>
        Split
      </span>
    );
  }
  if (method === "Personal") {
    return (
      <span className="bg-surface-container-highest text-on-surface-variant px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider flex items-center gap-1">
        <span className="material-symbols-outlined text-xs">person</span>
        Personal
      </span>
    );
  }
  return (
    <span className="bg-surface-container-highest text-on-surface-variant px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider flex items-center gap-1">
      <span className="material-symbols-outlined text-xs">person</span>
      Separate
    </span>
  );
}

export default function History() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const { userA, userB, mode } = useUsers();
  const isPersonal = mode === "personal";
  const isBlended = mode === "blended";
  const { fmt } = useCurrency();
  const { formatDate } = useDateFormat();
  const { showToast } = useToast();
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const searchRef = useRef(null);
  const prefill = location.state || {};

  // A fresh drill-down navigation (from Calendar/Analytics) always wins over
  // whatever filters happen to already be sitting in the URL; otherwise we
  // restore from the URL so filters survive an edit-and-return round trip.
  const initialFilters =
    prefill.start_date || prefill.month || prefill.category
      ? {
          appliedSearch: "",
          filterPaidBy: "",
          filterCategory: prefill.category || "",
          filterType: "",
          sortAmount: "",
          monthFilter: prefill.month || null,
          dateRange: prefill.start_date
            ? { start_date: prefill.start_date, end_date: prefill.end_date }
            : null,
        }
      : filtersFromSearchParams(searchParams);

  const [appliedSearch, setAppliedSearch] = useState(initialFilters.appliedSearch);
  const [monthFilter, setMonthFilter] = useState(initialFilters.monthFilter);
  const [dateRange, setDateRange] = useState(initialFilters.dateRange);
  const [filterPaidBy, setFilterPaidBy] = useState(initialFilters.filterPaidBy);
  const [filterCategory, setFilterCategory] = useState(initialFilters.filterCategory);
  const [sortAmount, setSortAmount] = useState(initialFilters.sortAmount);
  const [filterType, setFilterType] = useState(initialFilters.filterType);  // "" | "Personal" | "Shared"
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteError, setDeleteError] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [fetchError, setFetchError] = useState(null);
  const [showMergeModal, setShowMergeModal] = useState(false);
  const [suggestionCount, setSuggestionCount] = useState(0);

  // Keep the URL in sync with the active filters (replace, not push, so
  // every keystroke/select doesn't spam browser history) so they survive
  // navigating away (e.g. to edit a row) and back.
  useEffect(() => {
    setSearchParams(
      filtersToSearchParams({
        appliedSearch,
        filterPaidBy,
        filterCategory,
        filterType,
        sortAmount,
        monthFilter,
        dateRange,
      }),
      { replace: true },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appliedSearch, filterPaidBy, filterCategory, filterType, sortAmount, monthFilter, dateRange]);

  const fetchExpenses = useCallback(async (signal) => {
    setLoading(true);
    setFetchError(null);
    try {
      const params = buildExpenseParams({
        appliedSearch,
        filterPaidBy,
        filterCategory,
        dateRange,
        sortAmount,
        filterType,
      });
      const data = await getExpenses(params, { signal });
      if (signal?.aborted) return;
      setExpenses(data);
      setVisibleCount(PAGE_SIZE);
    } catch (err) {
      if (err.name === "AbortError") return;
      setFetchError("Failed to load expenses. Please check the server.");
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [appliedSearch, filterPaidBy, filterCategory, dateRange, sortAmount, filterType]);

  // AbortController so rapid preset/filter clicks can't render stale data
  // from an earlier, slower-to-resolve request.
  useEffect(() => {
    const controller = new AbortController();
    fetchExpenses(controller.signal);
    return () => controller.abort();
  }, [fetchExpenses]);

  const refreshSuggestionCount = useCallback(async () => {
    try {
      const results = await getSimilarDescriptions();
      setSuggestionCount(results.reduce((sum, c) => sum + c.groups.length, 0));
    } catch {
      // Non-critical — badge just won't show
    }
  }, []);

  useEffect(() => {
    refreshSuggestionCount();
  }, [refreshSuggestionCount]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setAppliedSearch(searchRef.current?.value || "");
  };

  const handleDeleteConfirm = async () => {
    if (deleting) return;
    setDeleteError("");
    setDeleting(true);
    try {
      await deleteExpense(deleteTarget.id);
      setDeleteTarget(null);
      showToast("Expense deleted.", "success");
      fetchExpenses();
    } catch {
      setDeleteError("Failed to delete. Please try again.");
    } finally {
      setDeleting(false);
    }
  };

  const handleExport = async () => {
    try {
      const params = buildExpenseParams({
        appliedSearch,
        filterPaidBy,
        filterCategory,
        dateRange,
        sortAmount,
        filterType,
      });
      await exportExpenses(params);
    } catch {
      showToast("Export failed. Please try again.", "error");
    }
  };

  const clearDrilldownFilter = () => {
    setMonthFilter(null);
    setDateRange(null);
    setFilterCategory("");
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-4xl font-headline font-extrabold text-on-surface tracking-tight mb-2">
            Detailed Expenses
          </h1>
          <p className="text-on-surface-variant font-medium">
            {isPersonal ? "Review and manage your expenses." : "Review and manage your shared financial journey."}
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowMergeModal(true)}
            className="relative bg-surface-container-high text-on-surface px-6 py-3 rounded-full font-headline font-bold flex items-center gap-2 hover:bg-surface-container-highest transition-colors active:scale-95"
            title={
              suggestionCount > 0
                ? `Clean up similar descriptions (${suggestionCount} suggestion${suggestionCount !== 1 ? "s" : ""} waiting)`
                : "Clean up similar descriptions"
            }
          >
            <span className="material-symbols-outlined">merge</span>
            Clean Up
            {suggestionCount > 0 && (
              <span
                className="absolute -top-1.5 -right-1.5 bg-tertiary text-on-tertiary text-[10px] font-bold min-w-[18px] h-[18px] rounded-full flex items-center justify-center px-1 shadow-sm"
                aria-label={`${suggestionCount} cleanup suggestions waiting`}
              >
                {suggestionCount > 99 ? "99+" : suggestionCount}
              </span>
            )}
          </button>
          <button
            onClick={handleExport}
            className="bg-surface-container-high text-on-surface px-6 py-3 rounded-full font-headline font-bold flex items-center gap-2 hover:bg-surface-container-highest transition-colors active:scale-95"
          >
            <span className="material-symbols-outlined">download</span>
            Export
          </button>
          <Link
            to="/add"
            className="bg-gradient-to-br from-primary to-primary-dim text-on-primary px-8 py-3 rounded-full font-headline font-bold flex items-center gap-2 shadow-[0_4px_24px_rgba(16,106,106,0.2)] active:scale-95 transition-transform"
          >
            <span
              className="material-symbols-outlined"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              add_circle
            </span>
            Add Expense
          </Link>
        </div>
      </header>

      {/* Drill-down filter pill — from Analytics (month) or Calendar (date range) */}
      {(monthFilter || dateRange) && (
        <div className="flex items-center gap-3">
          <div className="inline-flex items-center gap-2 bg-primary-container text-on-primary-container px-4 py-2 rounded-full text-sm font-bold">
            <span className="material-symbols-outlined text-[16px]">filter_alt</span>
            {monthFilter
              ? new Date(monthFilter + "-02").toLocaleDateString(undefined, { month: "long", year: "numeric" })
              : dateRange.start_date === dateRange.end_date
                ? formatDate(dateRange.start_date)
                : `${formatDate(dateRange.start_date)} – ${formatDate(dateRange.end_date)}`}
            {filterCategory && <><span className="opacity-50">·</span>{filterCategory}</>}
            <button
              onClick={clearDrilldownFilter}
              className="ml-1 hover:opacity-70 transition-opacity"
              aria-label="Clear filter"
            >
              <span className="material-symbols-outlined text-[16px]">close</span>
            </button>
          </div>
          <span className="text-xs text-on-surface-variant font-medium">
            {monthFilter ? "from Analytics" : "from Calendar"}
          </span>
        </div>
      )}

      {/* Search & Filters */}
      <section className="space-y-4">
        <form
          onSubmit={handleSearchSubmit}
          className="bg-surface-container-high rounded-3xl p-4 flex items-center gap-3"
        >
          <label htmlFor="expense-search" className="sr-only">Search transactions</label>
          <span className="material-symbols-outlined text-on-surface-variant">
            search
          </span>
          <input
            id="expense-search"
            type="text"
            ref={searchRef}
            defaultValue={appliedSearch}
            placeholder="Search transactions..."
            className="bg-transparent border-none focus:ring-0 w-full text-on-surface font-medium placeholder:text-outline"
          />
        </form>
        <div className={`grid grid-cols-1 ${isBlended ? "lg:grid-cols-4" : isPersonal ? "lg:grid-cols-2" : "lg:grid-cols-3"} gap-3`}>
          <div className="bg-surface-container rounded-3xl p-2 flex items-center justify-between px-4">
            <span className="text-on-surface-variant font-label font-semibold uppercase tracking-wider text-xs">
              Category
            </span>
            <select
              value={filterCategory}
              onChange={(e) => {
                setFilterCategory(e.target.value);
                setAppliedSearch(searchRef.current?.value || "");
              }}
              className="bg-transparent border-none focus:ring-0 text-primary font-bold pr-8 cursor-pointer"
            >
              <option value="">All</option>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          {!isPersonal && (
            <div className="bg-surface-container rounded-3xl p-2 flex items-center justify-between px-4">
              <span className="text-on-surface-variant font-label font-semibold uppercase tracking-wider text-xs">
                Paid By
              </span>
              <select
                value={filterPaidBy}
                onChange={(e) => {
                  setFilterPaidBy(e.target.value);
                  setAppliedSearch(searchRef.current?.value || "");
                }}
                className="bg-transparent border-none focus:ring-0 text-primary font-bold pr-8 cursor-pointer"
              >
                <option value="">All</option>
                <option value={userA}>{userA}</option>
                <option value={userB}>{userB}</option>
              </select>
            </div>
          )}
          {isBlended && (
            <div className="bg-surface-container rounded-3xl p-2 flex items-center justify-between px-4">
              <span className="text-on-surface-variant font-label font-semibold uppercase tracking-wider text-xs">
                Type
              </span>
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="bg-transparent border-none focus:ring-0 text-primary font-bold pr-8 cursor-pointer"
              >
                <option value="">All</option>
                <option value="Personal">Personal</option>
                <option value="Shared">Shared</option>
              </select>
            </div>
          )}
          <div className="bg-surface-container rounded-3xl p-2 flex items-center justify-between px-4">
            <span className="text-on-surface-variant font-label font-semibold uppercase tracking-wider text-xs">
              Amount
            </span>
            <select
              value={sortAmount}
              onChange={(e) => setSortAmount(e.target.value)}
              className="bg-transparent border-none focus:ring-0 text-primary font-bold pr-8 cursor-pointer"
            >
              <option value="">Default</option>
              <option value="desc">High to Low</option>
              <option value="asc">Low to High</option>
            </select>
          </div>
        </div>
      </section>

      {/* Table */}
      <div className="bg-surface-container-low rounded-3xl overflow-hidden shadow-sm">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          </div>
        ) : fetchError ? (
          <div className="text-center py-16 text-error text-sm">
            {fetchError}
          </div>
        ) : expenses.length === 0 ? (
          <div className="text-center py-16 text-on-surface-variant">
            <span className="material-symbols-outlined text-4xl mb-2 block opacity-40">
              receipt_long
            </span>
            No expenses found.
          </div>
        ) : (
          <>
            {/* Table Header (Desktop) */}
            <div className={`hidden md:grid ${isPersonal ? "md:grid-cols-8" : "md:grid-cols-12"} gap-4 px-8 py-5 bg-surface-container-highest border-b border-outline-variant/10 text-on-surface-variant font-label font-bold uppercase tracking-widest text-[11px]`}>
              <div className="col-span-1">Date</div>
              <div className={isPersonal ? "col-span-3" : "col-span-4"}>Description</div>
              <div className="col-span-2">Amount</div>
              {!isPersonal && <div className="col-span-2 text-center">Paid By</div>}
              {!isPersonal && <div className="col-span-2 text-center">Type</div>}
              <div className="col-span-1 text-right">Actions</div>
            </div>

            {/* Rows */}
            <div className="flex flex-col gap-3 p-3 md:p-4">
              {expenses.slice(0, visibleCount).map((expense) => (
                <div
                  key={expense.id}
                  className={`bg-surface-container-lowest rounded-2xl md:rounded-none md:bg-transparent md:hover:bg-surface-container transition-colors grid grid-cols-1 ${isPersonal ? "md:grid-cols-8" : "md:grid-cols-12"} gap-4 items-center px-6 py-6 group`}
                >
                  <div className="col-span-1 text-on-surface-variant font-medium md:text-sm whitespace-pre-line">
                    {formatDate(expense.date)}
                  </div>
                  <div className={`${isPersonal ? "col-span-3" : "col-span-4"} flex items-center gap-4`}>
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center ${CATEGORY_BG[expense.category] || CATEGORY_BG.Other}`}
                    >
                      <span className="material-symbols-outlined">
                        {CATEGORY_ICONS[expense.category] || "more_horiz"}
                      </span>
                    </div>
                    <div>
                      <p className="font-bold text-on-surface">
                        {expense.description}
                      </p>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-label font-bold uppercase tracking-tighter ${CATEGORY_BG[expense.category] || CATEGORY_BG.Other}`}
                      >
                        {expense.category}
                      </span>
                    </div>
                  </div>
                  <div className="col-span-2 text-xl font-headline font-bold text-on-surface">
                    {fmt(expense.amount)}
                  </div>
                  {!isPersonal && (
                    <div className="col-span-2 flex justify-center">
                      <div className="flex items-center gap-2 bg-surface-container px-3 py-1.5 rounded-full">
                        <Avatar user={expense.paid_by} size="sm" />
                        <span className="text-xs font-bold text-on-surface">
                          {expense.paid_by}
                        </span>
                      </div>
                    </div>
                  )}
                  {!isPersonal && (
                    <div className="col-span-2 flex justify-center">
                      {getSplitBadge(expense.split_method)}
                    </div>
                  )}
                  <div className="col-span-1 flex justify-end gap-2">
                    <button
                      onClick={() =>
                        navigate(`/edit/${expense.id}`, {
                          state: { returnTo: `/history${location.search}` },
                        })
                      }
                      className="p-2 rounded-lg hover:bg-surface-container-high text-outline transition-colors"
                      aria-label="Edit expense"
                    >
                      <span className="material-symbols-outlined" aria-hidden="true">edit</span>
                    </button>
                    <button
                      onClick={() => setDeleteTarget(expense)}
                      className="p-2 rounded-lg hover:bg-error-container/20 text-outline hover:text-error transition-colors"
                      aria-label="Delete expense"
                    >
                      <span className="material-symbols-outlined" aria-hidden="true">delete</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Footer */}
            <div className="p-6 bg-surface-container border-t border-outline-variant/10 flex flex-col sm:flex-row items-center justify-between gap-3">
              <p className="text-xs font-medium text-on-surface-variant">
                {visibleCount < expenses.length
                  ? `Showing ${visibleCount} of ${expenses.length} expenses`
                  : `Showing ${expenses.length} expense${expenses.length !== 1 ? "s" : ""}`}
              </p>
              {visibleCount < expenses.length && (
                <button
                  onClick={() => setVisibleCount((v) => v + PAGE_SIZE)}
                  className="bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-bold text-xs px-5 py-2.5 rounded-full transition-colors active:scale-95"
                >
                  Load {Math.min(PAGE_SIZE, expenses.length - visibleCount)} more
                </button>
              )}
            </div>
          </>
        )}
      </div>

      {/* Merge Descriptions Modal */}
      {showMergeModal && (
        <MergeDescriptionsModal
          onClose={() => {
            setShowMergeModal(false);
            refreshSuggestionCount();
          }}
          onMerged={() => {
            fetchExpenses();
            refreshSuggestionCount();
          }}
        />
      )}

      {/* Delete Confirmation */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-surface-container-lowest rounded-[2rem] shadow-xl max-w-sm w-full p-8">
            <div className="flex flex-col items-center text-center mb-6">
              <div className="w-16 h-16 rounded-full bg-error-container/20 flex items-center justify-center mb-4">
                <span className="material-symbols-outlined text-error text-3xl">
                  delete
                </span>
              </div>
              <h2 className="font-headline text-xl font-bold text-on-surface mb-2">
                Delete Expense
              </h2>
              <p className="text-on-surface-variant text-sm">
                Are you sure you want to delete &ldquo;
                <span className="font-medium">{deleteTarget.description}</span>
                &rdquo; ({fmt(deleteTarget.amount)})? This cannot be
                undone.
              </p>
            </div>
            {deleteError && (
              <p className="text-error text-sm text-center mb-4">{deleteError}</p>
            )}
            <div className="flex gap-3">
              <button
                onClick={() => { setDeleteTarget(null); setDeleteError(""); }}
                disabled={deleting}
                className="flex-1 bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-bold rounded-full px-4 py-3 transition-colors disabled:opacity-60"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirm}
                disabled={deleting}
                className="flex-1 bg-error hover:bg-error-dim text-on-error font-bold rounded-full px-4 py-3 transition-colors disabled:opacity-60"
              >
                {deleting ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
