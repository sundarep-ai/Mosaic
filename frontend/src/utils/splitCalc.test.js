import { describe, it, expect } from "vitest";
import { computeSplit } from "./splitCalc";

const A = "Alice";
const B = "Bob";

describe("computeSplit", () => {
  it("returns zeros for an empty item list", () => {
    expect(computeSplit([], 0, A, A, B)).toEqual({
      subtotal: 0,
      tax: 0,
      total: 0,
      netOwed: 0,
      ower: B,
    });
  });

  it("an item owned by the payer contributes nothing owed", () => {
    const items = [{ amount: 50, owner: A, taxable: false }];
    expect(computeSplit(items, 0, A, A, B).netOwed).toBe(0);
  });

  it("an item owned by the other person is owed in full", () => {
    const items = [{ amount: 20, owner: B, taxable: false }];
    const result = computeSplit(items, 0, A, A, B);
    expect(result.netOwed).toBe(20);
    expect(result.ower).toBe(B);
  });

  it("a shared item is owed at half", () => {
    const items = [{ amount: 6, owner: "Shared", taxable: false }];
    expect(computeSplit(items, 0, A, A, B).netOwed).toBe(3);
  });

  it("applies tax only to taxable items", () => {
    const items = [
      { amount: 20, owner: B, taxable: true },
      { amount: 8, owner: B, taxable: false },
    ];
    const result = computeSplit(items, 13, A, A, B);
    expect(result.tax).toBe(2.6);
    expect(result.subtotal).toBe(28);
    expect(result.total).toBe(30.6);
    expect(result.netOwed).toBe(30.6);
  });

  it("mixes owners and taxability in one bill", () => {
    // Alice paid. Milk ($6, shared, taxable) + Bob's book ($20, his, not
    // taxable) + Alice's razor ($8, hers, taxable). Tax 13%.
    const items = [
      { amount: 6, owner: "Shared", taxable: true },
      { amount: 20, owner: B, taxable: false },
      { amount: 8, owner: A, taxable: true },
    ];
    const result = computeSplit(items, 13, A, A, B);
    // Bob owes: half of (6 + 6*0.13) + 20 = half of 6.78 + 20 = 3.39 + 20
    expect(result.netOwed).toBe(23.39);
    expect(result.ower).toBe(B);
  });

  it("switches direction when the other person is the payer", () => {
    const items = [{ amount: 10, owner: A, taxable: false }];
    const result = computeSplit(items, 0, B, A, B);
    expect(result.netOwed).toBe(10);
    expect(result.ower).toBe(A);
  });

  it("ignores items with a zero or missing amount", () => {
    const items = [
      { amount: 0, owner: B, taxable: false },
      { amount: "", owner: B, taxable: false },
      { amount: 5, owner: B, taxable: false },
    ];
    const result = computeSplit(items, 0, A, A, B);
    expect(result.subtotal).toBe(5);
    expect(result.netOwed).toBe(5);
  });

  it("rounds to 2 decimal places", () => {
    const items = [{ amount: 10, owner: "Shared", taxable: true }];
    const result = computeSplit(items, 12.5, A, A, B);
    // 10 * 1.125 = 11.25, half = 5.625 -> rounds to 5.63
    expect(result.netOwed).toBe(5.63);
  });
});
