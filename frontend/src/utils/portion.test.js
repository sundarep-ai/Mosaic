import { describe, it, expect } from "vitest";
import { calcMyPortion, sumMyPortion } from "./portion";

const ME = "Alice";
const OTHER = "Bob";

function makeExpense(overrides = {}) {
  return {
    amount: 100,
    split_method: "50/50",
    paid_by: ME,
    category: "Groceries",
    ...overrides,
  };
}

describe("calcMyPortion", () => {
  // ── Personal ──

  it("returns full amount for Personal paid by me", () => {
    expect(calcMyPortion(makeExpense({ split_method: "Personal", paid_by: ME }), ME, OTHER))
      .toBe(100);
  });

  it("returns 0 for Personal paid by other", () => {
    expect(calcMyPortion(makeExpense({ split_method: "Personal", paid_by: OTHER }), ME, OTHER))
      .toBe(0);
  });

  // ── 50/50 ──

  it("returns half for 50/50 paid by me", () => {
    expect(calcMyPortion(makeExpense({ split_method: "50/50", paid_by: ME }), ME, OTHER))
      .toBe(50);
  });

  it("returns half for 50/50 paid by other", () => {
    expect(calcMyPortion(makeExpense({ split_method: "50/50", paid_by: OTHER }), ME, OTHER))
      .toBe(50);
  });

  // ── 100% me ──

  it("returns full amount for 100% me (paid by other)", () => {
    expect(calcMyPortion(makeExpense({ split_method: `100% ${ME}`, paid_by: OTHER }), ME, OTHER))
      .toBe(100);
  });

  // ── 100% other ──

  it("returns 0 for 100% other (paid by me)", () => {
    expect(calcMyPortion(makeExpense({ split_method: `100% ${OTHER}`, paid_by: ME }), ME, OTHER))
      .toBe(0);
  });

  // ── Category exclusions ──

  it("returns 0 for Payment category", () => {
    expect(calcMyPortion(makeExpense({ category: "Payment" }), ME, OTHER))
      .toBe(0);
  });

  it("returns 0 for Reimbursement category", () => {
    expect(calcMyPortion(makeExpense({ category: "Reimbursement", amount: -30 }), ME, OTHER))
      .toBe(0);
  });
});

describe("sumMyPortion", () => {
  it("sums portions across multiple expenses", () => {
    const expenses = [
      makeExpense({ split_method: "50/50", amount: 100 }),           // 50
      makeExpense({ split_method: "Personal", paid_by: ME, amount: 20 }), // 20
      makeExpense({ split_method: `100% ${OTHER}`, paid_by: ME, amount: 60 }), // 0
    ];
    expect(sumMyPortion(expenses, ME, OTHER)).toBe(70);
  });

  it("returns 0 for empty array", () => {
    expect(sumMyPortion([], ME, OTHER)).toBe(0);
  });

  it("excludes Payment and Reimbursement from sum", () => {
    const expenses = [
      makeExpense({ split_method: "50/50", amount: 100 }),     // 50
      makeExpense({ category: "Payment", amount: 200 }),       // 0
      makeExpense({ category: "Reimbursement", amount: -50 }), // 0
    ];
    expect(sumMyPortion(expenses, ME, OTHER)).toBe(50);
  });
});
