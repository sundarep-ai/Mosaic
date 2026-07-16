import { describe, it, expect } from "vitest";
import {
  getAttention,
  hasWeekendData,
  hasIncomeData,
  getSectionVisibility,
  hasAnySection,
  getForecastLine,
} from "./insightsView";

describe("getAttention", () => {
  it("reports hasAny false when every attention array is empty or missing", () => {
    expect(getAttention({}).hasAny).toBe(false);
    expect(getAttention(undefined).hasAny).toBe(false);
    expect(
      getAttention({
        recurring_alerts: [],
        new_subscription_alerts: [],
        category_trend_alerts: [],
        anomalies: [],
      }).hasAny,
    ).toBe(false);
  });

  it("passes through each array and flags hasAny when any is non-empty", () => {
    const data = {
      recurring_alerts: [{ description: "Netflix" }],
      new_subscription_alerts: [{ description: "Disney+" }],
      category_trend_alerts: [{ category: "Dining" }],
      anomalies: [{ id: 1 }],
    };
    const a = getAttention(data);
    expect(a.recurring_alerts).toEqual(data.recurring_alerts);
    expect(a.new_subscription_alerts).toEqual(data.new_subscription_alerts);
    expect(a.category_trend_alerts).toEqual(data.category_trend_alerts);
    expect(a.anomalies).toEqual(data.anomalies);
    expect(a.hasAny).toBe(true);
  });

  it("flags hasAny when only anomalies exist", () => {
    expect(getAttention({ anomalies: [{ id: 1 }] }).hasAny).toBe(true);
  });

  it("flags hasAny when only new subscription alerts exist", () => {
    expect(getAttention({ new_subscription_alerts: [{ description: "x" }] }).hasAny).toBe(true);
  });
});

describe("hasWeekendData", () => {
  const withCounts = (wd, we) => ({
    your_expense: {
      weekday: { count: wd, total: 0, by_category: [] },
      weekend: { count: we, total: 0, by_category: [] },
    },
  });

  it("is false for missing / empty data", () => {
    expect(hasWeekendData(undefined)).toBe(false);
    expect(hasWeekendData({})).toBe(false);
    expect(hasWeekendData(withCounts(0, 0))).toBe(false);
  });

  it("is true when there is at least one transaction on either side", () => {
    expect(hasWeekendData(withCounts(1, 0))).toBe(true);
    expect(hasWeekendData(withCounts(0, 3))).toBe(true);
  });
});

describe("hasIncomeData", () => {
  it("is false when income is missing or has no logged income", () => {
    expect(hasIncomeData(null)).toBe(false);
    expect(hasIncomeData({ savings_rate: { trend: [], current_month: { income: 0 } } })).toBe(false);
  });

  it("is true when the trend has income", () => {
    expect(
      hasIncomeData({ savings_rate: { trend: [{ income: 0 }, { income: 500 }] } }),
    ).toBe(true);
  });

  it("is true when the current month has income even if the trend is empty", () => {
    expect(hasIncomeData({ savings_rate: { trend: [], current_month: { income: 200 } } })).toBe(true);
  });
});

describe("getSectionVisibility", () => {
  it("hides every section for an empty payload", () => {
    const v = getSectionVisibility({}, true);
    expect(v).toEqual({
      forecast: false,
      recurring: false,
      weekend: false,
      topGrowing: false,
      income: false,
    });
  });

  it("shows forecast only when total_forecast is positive", () => {
    expect(getSectionVisibility({ forecast: { total_forecast: 0 } }).forecast).toBe(false);
    expect(getSectionVisibility({ forecast: { total_forecast: 10 } }).forecast).toBe(true);
  });

  it("shows recurring / top-growing based on array length", () => {
    const v = getSectionVisibility({
      recurring_expenses: [{ description: "x" }],
      top_growing_categories: [{ category: "Dining" }],
    });
    expect(v.recurring).toBe(true);
    expect(v.topGrowing).toBe(true);
  });

  it("hides income when incomeEnabled is false even if income data exists", () => {
    const income_insights = { savings_rate: { current_month: { income: 999 } } };
    expect(getSectionVisibility({ income_insights }, false).income).toBe(false);
    expect(getSectionVisibility({ income_insights }, true).income).toBe(true);
  });
});

describe("hasAnySection", () => {
  it("is false when nothing is visible", () => {
    expect(hasAnySection({ forecast: false, recurring: false, weekend: false, topGrowing: false, income: false })).toBe(false);
  });
  it("is true when any single section is visible", () => {
    expect(hasAnySection({ forecast: false, recurring: true, weekend: false, topGrowing: false, income: false })).toBe(true);
  });
});

describe("getForecastLine", () => {
  const fmt = (n) => `$${n.toFixed(2)}`;

  it("returns null when forecast is missing", () => {
    expect(getForecastLine(null, fmt)).toBeNull();
    expect(getForecastLine(undefined, fmt)).toBeNull();
  });

  it("returns null when there is no positive figure", () => {
    expect(getForecastLine({ total_forecast: 0 }, fmt)).toBeNull();
    expect(getForecastLine({ total_forecast: 0, on_pace: { estimated_total: 0 } }, fmt)).toBeNull();
  });

  it("returns the one-line summary from total_forecast when on_pace is absent", () => {
    expect(getForecastLine({ total_forecast: 2340 }, fmt)).toBe(
      "On track for ~$2340.00 this month",
    );
  });

  it("prefers on_pace.estimated_total when present and positive", () => {
    expect(
      getForecastLine({ total_forecast: 2340, on_pace: { estimated_total: 1800 } }, fmt),
    ).toBe("On track for ~$1800.00 this month");
  });

  it("falls back to total_forecast when on_pace is zero", () => {
    expect(
      getForecastLine({ total_forecast: 2340, on_pace: { estimated_total: 0 } }, fmt),
    ).toBe("On track for ~$2340.00 this month");
  });
});
