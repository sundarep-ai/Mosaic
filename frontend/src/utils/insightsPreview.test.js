import { describe, it, expect } from "vitest";
import { selectTopAlerts, getForecastLine } from "./insightsPreview";

describe("selectTopAlerts", () => {
  it("returns empty arrays when there are no alerts", () => {
    expect(selectTopAlerts([], [])).toEqual({ recurring: [], trend: [] });
  });

  it("takes recurring alerts first, up to max", () => {
    const recurring = [{ id: 1 }, { id: 2 }, { id: 3 }];
    expect(selectTopAlerts(recurring, [])).toEqual({
      recurring: [{ id: 1 }, { id: 2 }],
      trend: [],
    });
  });

  it("fills remaining slots from category trend alerts", () => {
    const recurring = [{ id: 1 }];
    const trend = [{ cat: "A" }, { cat: "B" }];
    expect(selectTopAlerts(recurring, trend)).toEqual({
      recurring: [{ id: 1 }],
      trend: [{ cat: "A" }],
    });
  });

  it("returns only trend alerts when there are no recurring alerts", () => {
    const trend = [{ cat: "A" }, { cat: "B" }, { cat: "C" }];
    expect(selectTopAlerts([], trend)).toEqual({
      recurring: [],
      trend: [{ cat: "A" }, { cat: "B" }],
    });
  });

  it("respects a custom max", () => {
    const recurring = [{ id: 1 }, { id: 2 }];
    const trend = [{ cat: "A" }];
    expect(selectTopAlerts(recurring, trend, 1)).toEqual({
      recurring: [{ id: 1 }],
      trend: [],
    });
  });
});

describe("getForecastLine", () => {
  const fmt = (n) => `$${n.toFixed(2)}`;

  it("returns null when forecast is missing", () => {
    expect(getForecastLine(null, fmt)).toBeNull();
    expect(getForecastLine(undefined, fmt)).toBeNull();
  });

  it("returns null when total_forecast is zero", () => {
    expect(getForecastLine({ total_forecast: 0 }, fmt)).toBeNull();
  });

  it("returns the one-line summary when total_forecast is positive", () => {
    expect(getForecastLine({ total_forecast: 2340 }, fmt)).toBe(
      "On track for ~$2340.00 this month",
    );
  });

  it("prefers on_pace.estimated_total when present", () => {
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
