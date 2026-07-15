/**
 * Shared filter-state helpers for the History page.
 *
 * Centralizing this logic means the expense-list fetch and the export
 * download can never drift apart (both build their query params from the
 * same function), and filter state can round-trip through the URL so it
 * survives navigation away (e.g. to edit a row) and back.
 */

export function buildExpenseParams({
  appliedSearch,
  filterPaidBy,
  filterCategory,
  dateRange,
  sortAmount,
  filterType,
} = {}) {
  const params = {};
  if (appliedSearch) params.search = appliedSearch;
  if (filterPaidBy) params.paid_by = filterPaidBy;
  if (filterCategory) params.category = filterCategory;
  if (dateRange) {
    params.start_date = dateRange.start_date;
    params.end_date = dateRange.end_date;
  }
  if (sortAmount) {
    params.sort_by = "amount";
    params.sort = sortAmount;
  }
  if (filterType === "Personal") params.filter_type = "personal";
  else if (filterType === "Shared") params.filter_type = "shared";
  return params;
}

export function filtersToSearchParams(filters) {
  const sp = new URLSearchParams();
  if (filters.appliedSearch) sp.set("q", filters.appliedSearch);
  if (filters.filterPaidBy) sp.set("paid_by", filters.filterPaidBy);
  if (filters.filterCategory) sp.set("category", filters.filterCategory);
  if (filters.filterType) sp.set("type", filters.filterType);
  if (filters.sortAmount) sp.set("sort", filters.sortAmount);
  if (filters.monthFilter) sp.set("month", filters.monthFilter);
  if (filters.dateRange) {
    sp.set("start_date", filters.dateRange.start_date);
    sp.set("end_date", filters.dateRange.end_date);
  }
  return sp;
}

export function filtersFromSearchParams(searchParams) {
  const start_date = searchParams.get("start_date");
  const end_date = searchParams.get("end_date");
  return {
    appliedSearch: searchParams.get("q") || "",
    filterPaidBy: searchParams.get("paid_by") || "",
    filterCategory: searchParams.get("category") || "",
    filterType: searchParams.get("type") || "",
    sortAmount: searchParams.get("sort") || "",
    monthFilter: searchParams.get("month") || null,
    dateRange: start_date && end_date ? { start_date, end_date } : null,
  };
}
