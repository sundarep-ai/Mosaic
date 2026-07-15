/**
 * Pure math for the itemized split calculator.
 *
 * An item's `owner` is one of the two display names (`userA`/`userB`) or the
 * literal string "Shared". Whoever paid the whole bill (`payer`) can only be
 * owed money by the other person — an item owned by the payer contributes
 * nothing to what's owed, an item owned by the other person contributes its
 * full effective amount, and a Shared item contributes half.
 */

function round2(n) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

/**
 * @param {Array<{amount: number|string, owner: string, taxable: boolean}>} items
 * @param {number|string} taxPct - tax percentage applied to taxable items only
 * @param {string} payer - display name of whoever paid the bill
 * @param {string} userA
 * @param {string} userB
 * @returns {{subtotal: number, tax: number, total: number, netOwed: number, ower: string}}
 */
export function computeSplit(items, taxPct, payer, userA, userB) {
  const other = payer === userA ? userB : userA;
  const taxRate = (Number(taxPct) || 0) / 100;

  let subtotal = 0;
  let tax = 0;
  let netOwed = 0;

  for (const item of items) {
    const amt = Number(item.amount) || 0;
    if (!amt) continue;

    subtotal += amt;
    const itemTax = item.taxable ? amt * taxRate : 0;
    tax += itemTax;
    const effective = amt + itemTax;

    if (item.owner === other) {
      netOwed += effective;
    } else if (item.owner === "Shared") {
      netOwed += effective / 2;
    }
    // item.owner === payer contributes 0 — it was always theirs to cover.
  }

  return {
    subtotal: round2(subtotal),
    tax: round2(tax),
    total: round2(subtotal + tax),
    netOwed: round2(netOwed),
    ower: other,
  };
}
