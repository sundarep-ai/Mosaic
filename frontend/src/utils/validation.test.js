import { describe, it, expect } from "vitest";
import { validateExpense } from "./validation";

const TODAY = "2026-03-30";

function makeForm(overrides = {}) {
  return {
    description: "Groceries",
    amount: "50",
    category: "Groceries",
    date: "2026-03-15",
    paid_by: "Praveen",
    split_method: "50/50",
    ...overrides,
  };
}

describe("validateExpense", () => {
  it("returns null for a valid expense", () => {
    expect(validateExpense(makeForm(), { today: TODAY })).toBeNull();
  });

  // ── Description ──

  it("rejects empty description", () => {
    expect(validateExpense(makeForm({ description: "" }), { today: TODAY }))
      .toBe("Description is required.");
  });

  it("rejects whitespace-only description", () => {
    expect(validateExpense(makeForm({ description: "   " }), { today: TODAY }))
      .toBe("Description is required.");
  });

  // ── Category ──

  it("rejects empty category with custom category enabled", () => {
    expect(validateExpense(makeForm(), { isCustomCategory: true, customCategory: "", today: TODAY }))
      .toBe("Category is required.");
  });

  it("accepts valid custom category", () => {
    expect(validateExpense(makeForm(), { isCustomCategory: true, customCategory: "Pets", today: TODAY }))
      .toBeNull();
  });

  // ── Amount ──

  it("rejects zero amount", () => {
    expect(validateExpense(makeForm({ amount: "0" }), { today: TODAY }))
      .toBe("Amount cannot be zero.");
  });

  it("rejects empty amount", () => {
    expect(validateExpense(makeForm({ amount: "" }), { today: TODAY }))
      .toBe("Amount cannot be zero.");
  });

  it("rejects negative amount for non-Reimbursement", () => {
    expect(validateExpense(makeForm({ amount: "-10", category: "Groceries" }), { today: TODAY }))
      .toBe("Negative amounts are only allowed for Reimbursement.");
  });

  it("allows negative amount for Reimbursement", () => {
    expect(validateExpense(makeForm({ amount: "-10", category: "Reimbursement" }), { today: TODAY }))
      .toBeNull();
  });

  it("accepts positive amount", () => {
    expect(validateExpense(makeForm({ amount: "99.99" }), { today: TODAY }))
      .toBeNull();
  });

  // ── Date ──

  it("rejects future date", () => {
    expect(validateExpense(makeForm({ date: "2026-04-01" }), { today: TODAY }))
      .toBe("Date cannot be in the future.");
  });

  it("accepts today's date", () => {
    expect(validateExpense(makeForm({ date: TODAY }), { today: TODAY }))
      .toBeNull();
  });

  it("accepts past date", () => {
    expect(validateExpense(makeForm({ date: "2025-01-01" }), { today: TODAY }))
      .toBeNull();
  });

  // ── Split method ──

  it("rejects 100% split assigned to the payer", () => {
    expect(validateExpense(makeForm({ paid_by: "Praveen", split_method: "100% Praveen" }), { today: TODAY }))
      .toBe("Split method cannot assign 100% to the person who paid.");
  });

  it("accepts 100% split assigned to the other person", () => {
    expect(validateExpense(makeForm({ paid_by: "Praveen", split_method: "100% Nina" }), { today: TODAY }))
      .toBeNull();
  });
});
