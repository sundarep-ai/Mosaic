import { describe, it, expect } from "vitest";
import { getSplitPreview } from "./splitPreview";

const ME = "Alice";
const OTHER = "Bob";
const fmt = (n) => `$${n.toFixed(2)}`;

function makeExpense(overrides = {}) {
  return {
    amount: 100,
    split_method: "50/50",
    paid_by: ME,
    category: "Groceries",
    ...overrides,
  };
}

describe("getSplitPreview", () => {
  it("says I'll owe half when other paid 50/50", () => {
    expect(getSplitPreview(makeExpense({ paid_by: OTHER }), ME, OTHER, fmt))
      .toBe("50/50 → you'll owe Bob $50.00.");
  });

  it("says other will owe me half when I paid 50/50", () => {
    expect(getSplitPreview(makeExpense({ paid_by: ME }), ME, OTHER, fmt))
      .toBe("50/50 → Bob will owe you $50.00.");
  });

  it("says I'll owe the full amount when other paid and I owe 100%", () => {
    expect(getSplitPreview(makeExpense({ split_method: `100% ${ME}`, paid_by: OTHER }), ME, OTHER, fmt))
      .toBe("100% → you'll owe Bob $100.00.");
  });

  it("says other will owe me the full amount when I paid and other owes 100%", () => {
    expect(getSplitPreview(makeExpense({ split_method: `100% ${OTHER}`, paid_by: ME }), ME, OTHER, fmt))
      .toBe("100% → Bob will owe you $100.00.");
  });

  it("says balance is unaffected for Personal paid by me", () => {
    expect(getSplitPreview(makeExpense({ split_method: "Personal", paid_by: ME }), ME, OTHER, fmt))
      .toBe("Personal — won't affect your shared balance.");
  });

  it("says balance is unaffected for Personal paid by other, naming them", () => {
    expect(getSplitPreview(makeExpense({ split_method: "Personal", paid_by: OTHER }), ME, OTHER, fmt))
      .toBe("Personal — paid by Bob, won't affect your shared balance.");
  });

  it("returns null for Payment category (settle-up states its own direction)", () => {
    expect(getSplitPreview(makeExpense({ category: "Payment" }), ME, OTHER, fmt)).toBeNull();
  });

  it("returns null when amount is zero or missing", () => {
    expect(getSplitPreview(makeExpense({ amount: 0 }), ME, OTHER, fmt)).toBeNull();
    expect(getSplitPreview(makeExpense({ amount: NaN }), ME, OTHER, fmt)).toBeNull();
  });

  it("returns null when there is no partner (personal mode)", () => {
    expect(getSplitPreview(makeExpense(), ME, "", fmt)).toBeNull();
  });
});
