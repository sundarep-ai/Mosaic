import { describe, it, expect } from "vitest";
import { buildSankeyData } from "./SankeyChart";

function sankeyResp(overrides = {}) {
  return {
    income_total: 1000,
    by_source: [{ source: "Salary / Wages", amount: 1000 }],
    expenses_total: 800,
    by_category: [{ category: "Rent", amount: 800 }],
    savings: 200,
    ...overrides,
  };
}

describe("buildSankeyData", () => {
  it("returns null when there is no income", () => {
    expect(buildSankeyData(sankeyResp({ income_total: 0 }))).toBeNull();
  });

  it("adds a Savings node when savings is positive", () => {
    const data = buildSankeyData(sankeyResp());
    expect(data.nodes.some((n) => n.name === "Savings")).toBe(true);
    expect(data.deficit).toBe(0);
  });

  it("reports a deficit and omits the Savings node on an overspend month", () => {
    const data = buildSankeyData(
      sankeyResp({ expenses_total: 1200, by_category: [{ category: "Rent", amount: 1200 }], savings: -200 })
    );
    expect(data.nodes.some((n) => n.name === "Savings")).toBe(false);
    expect(data.deficit).toBe(200);
  });

  it("treats sub-cent negative savings as settled, not a deficit", () => {
    const data = buildSankeyData(sankeyResp({ savings: -0.001 }));
    expect(data.deficit).toBe(0);
  });
});
