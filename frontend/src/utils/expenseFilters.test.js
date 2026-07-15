import { describe, it, expect } from "vitest";
import {
  buildExpenseParams,
  filtersToSearchParams,
  filtersFromSearchParams,
} from "./expenseFilters";

describe("buildExpenseParams", () => {
  it("returns an empty object when nothing is set", () => {
    expect(buildExpenseParams({})).toEqual({});
  });

  it("includes search, paid_by, and category when set", () => {
    expect(
      buildExpenseParams({
        appliedSearch: "coffee",
        filterPaidBy: "Alice",
        filterCategory: "Dining",
      }),
    ).toEqual({ search: "coffee", paid_by: "Alice", category: "Dining" });
  });

  it("includes start_date/end_date when dateRange is set", () => {
    expect(
      buildExpenseParams({
        dateRange: { start_date: "2024-05-01", end_date: "2024-05-31" },
      }),
    ).toEqual({ start_date: "2024-05-01", end_date: "2024-05-31" });
  });

  it("maps sortAmount to sort_by=amount + sort direction", () => {
    expect(buildExpenseParams({ sortAmount: "desc" })).toEqual({
      sort_by: "amount",
      sort: "desc",
    });
  });

  it("maps filterType Personal/Shared to filter_type personal/shared", () => {
    expect(buildExpenseParams({ filterType: "Personal" })).toEqual({
      filter_type: "personal",
    });
    expect(buildExpenseParams({ filterType: "Shared" })).toEqual({
      filter_type: "shared",
    });
  });

  it("ignores an unrecognized filterType value", () => {
    expect(buildExpenseParams({ filterType: "" })).toEqual({});
  });

  it("combines every filter together", () => {
    expect(
      buildExpenseParams({
        appliedSearch: "gas",
        filterPaidBy: "Bob",
        filterCategory: "Gas",
        dateRange: { start_date: "2024-01-01", end_date: "2024-01-31" },
        sortAmount: "asc",
        filterType: "Shared",
      }),
    ).toEqual({
      search: "gas",
      paid_by: "Bob",
      category: "Gas",
      start_date: "2024-01-01",
      end_date: "2024-01-31",
      sort_by: "amount",
      sort: "asc",
      filter_type: "shared",
    });
  });
});

describe("filtersToSearchParams / filtersFromSearchParams round-trip", () => {
  it("round-trips a full filter set", () => {
    const filters = {
      appliedSearch: "coffee",
      filterPaidBy: "Alice",
      filterCategory: "Dining",
      filterType: "Personal",
      sortAmount: "desc",
      monthFilter: "2024-05",
      dateRange: { start_date: "2024-05-01", end_date: "2024-05-31" },
    };
    const sp = filtersToSearchParams(filters);
    expect(filtersFromSearchParams(sp)).toEqual(filters);
  });

  it("round-trips an empty filter set back to defaults", () => {
    const sp = filtersToSearchParams({});
    expect(filtersFromSearchParams(sp)).toEqual({
      appliedSearch: "",
      filterPaidBy: "",
      filterCategory: "",
      filterType: "",
      sortAmount: "",
      monthFilter: null,
      dateRange: null,
    });
  });

  it("treats a dateRange missing end_date as absent", () => {
    const sp = new URLSearchParams({ start_date: "2024-05-01" });
    expect(filtersFromSearchParams(sp).dateRange).toBeNull();
  });
});
