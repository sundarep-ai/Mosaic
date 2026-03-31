import { describe, it, expect } from "vitest";
import { getDateRange, groupByDescription, groupByMonth } from "./analytics";

// ── getDateRange ────────────────────────────────────────────────────

describe("getDateRange", () => {
  it("subtracts 30 days for 1M", () => {
    const now = new Date("2026-04-15T12:00:00");
    const { start_date, end_date } = getDateRange(30, now);
    expect(end_date).toBe("2026-04-15");
    expect(start_date).toBe("2026-03-16");
  });

  it("does not overflow when current day > 28 (the original bug)", () => {
    // March 30 minus 30 days should land in February, not roll to March
    const now = new Date("2026-03-30T12:00:00");
    const { start_date } = getDateRange(30, now);
    expect(start_date).toBe("2026-02-28");
  });

  it("handles March 31 minus 30 days", () => {
    const now = new Date("2026-03-31T12:00:00");
    const { start_date } = getDateRange(30, now);
    expect(start_date).toBe("2026-03-01");
  });

  it("handles 1Y (365 days)", () => {
    const now = new Date("2026-03-30T12:00:00");
    const { start_date } = getDateRange(365, now);
    expect(start_date).toBe("2025-03-30");
  });

  it("crosses year boundary correctly", () => {
    const now = new Date("2026-01-15T12:00:00");
    const { start_date } = getDateRange(30, now);
    expect(start_date).toBe("2025-12-16");
  });

  it("handles leap year", () => {
    // 2028 is a leap year; March 1 minus 1 day = Feb 29
    const now = new Date("2028-03-01T12:00:00");
    const { start_date } = getDateRange(1, now);
    expect(start_date).toBe("2028-02-29");
  });

  it("91 days for 3M", () => {
    const now = new Date("2026-06-15T12:00:00");
    const { start_date } = getDateRange(91, now);
    expect(start_date).toBe("2026-03-16");
  });
});

// ── groupByDescription ──────────────────────────────────────────────

describe("groupByDescription", () => {
  const expenses = [
    { description: "Costco", amount: 80, date: "2026-03-01" },
    { description: "Costco", amount: 120, date: "2026-03-05" },
    { description: "Walmart", amount: 50, date: "2026-03-02" },
    { description: "Gas", amount: 45, date: "2026-03-03" },
  ];

  it("groups and sums amounts by description", () => {
    const result = groupByDescription(expenses);
    const costco = result.find((g) => g.description === "Costco");
    expect(costco.amount).toBe(200);
    expect(costco.count).toBe(2);
  });

  it("sorts by amount descending", () => {
    const result = groupByDescription(expenses);
    expect(result[0].description).toBe("Costco");
    expect(result[1].description).toBe("Walmart");
  });

  it("respects the limit parameter", () => {
    const result = groupByDescription(expenses, 2);
    expect(result).toHaveLength(2);
  });

  it("returns empty array for empty input", () => {
    expect(groupByDescription([])).toEqual([]);
  });
});

// ── groupByMonth ────────────────────────────────────────────────────

describe("groupByMonth", () => {
  const expenses = [
    { description: "A", amount: 100, date: "2026-01-15" },
    { description: "B", amount: 50, date: "2026-01-20" },
    { description: "C", amount: 200, date: "2026-03-01" },
    { description: "D", amount: 75, date: "2026-02-10" },
  ];

  it("groups and sums by month", () => {
    const result = groupByMonth(expenses);
    const jan = result.find((g) => g.month === "2026-01");
    expect(jan.amount).toBe(150);
    expect(jan.count).toBe(2);
  });

  it("sorts chronologically", () => {
    const result = groupByMonth(expenses);
    expect(result.map((g) => g.month)).toEqual(["2026-01", "2026-02", "2026-03"]);
  });

  it("returns empty array for empty input", () => {
    expect(groupByMonth([])).toEqual([]);
  });
});
