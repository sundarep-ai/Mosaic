import { calcMyPortion } from "./portion";

/**
 * Compute the "under the amount" sentence describing how an expense will
 * move the shared balance, from the current user's perspective.
 *
 * @param {Object} expense - { amount, split_method, paid_by, category }
 * @param {string} me - current user's display name
 * @param {string} other - partner's display name
 * @param {(n: number) => string} fmt - currency formatter (e.g. from CurrencyContext)
 * @returns {string|null} the preview sentence, or null when there's nothing to show
 */
export function getSplitPreview(expense, me, other, fmt) {
  const { amount, split_method, paid_by, category } = expense;

  if (!amount || amount <= 0 || !other) return null;

  if (split_method === "Personal") {
    return paid_by === me
      ? "Personal — won't affect your shared balance."
      : `Personal — paid by ${other}, won't affect your shared balance.`;
  }

  // Settle-up payments state their own direction on this screen already.
  if (category === "Payment") return null;

  const myPortion = calcMyPortion({ amount, split_method, paid_by, category }, me, other);
  const amountIPaid = paid_by === me ? amount : 0;
  const net = myPortion - amountIPaid;

  const label = split_method === "50/50" ? "50/50" : "100%";

  if (Math.abs(net) < 0.005) return `${label} — this won't change your balance.`;
  if (net > 0) return `${label} → you'll owe ${other} ${fmt(net)}.`;
  return `${label} → ${other} will owe you ${fmt(Math.abs(net))}.`;
}
