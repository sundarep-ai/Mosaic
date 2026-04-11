/**
 * Calculate the current user's portion of a single expense.
 * @param {Object} expense - { amount, split_method, paid_by, category }
 * @param {string} me - current user's display name
 * @param {string} other - partner's display name
 * @returns {number} the user's portion of the expense
 */
export function calcMyPortion(expense, me, other) {
  const { amount, split_method, paid_by, category } = expense;

  if (category === "Payment") return 0;
  // Reimbursement flows through — its negative amount naturally reduces the total

  if (split_method === "Personal") return paid_by === me ? amount : 0;
  if (split_method === "50/50") return amount / 2;
  if (split_method === `100% ${me}`) return amount;
  if (split_method === `100% ${other}`) return 0;

  return 0;
}

/**
 * Sum the user's portion across an array of expenses.
 * @param {Array} expenses
 * @param {string} me - current user's display name
 * @param {string} other - partner's display name
 * @returns {number}
 */
export function sumMyPortion(expenses, me, other) {
  return expenses.reduce((sum, e) => sum + calcMyPortion(e, me, other), 0);
}
