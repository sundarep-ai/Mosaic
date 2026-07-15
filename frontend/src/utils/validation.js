import { CATEGORIES } from "../constants/categories";

/**
 * Validate an expense form and return an error string, or null if valid.
 *
 * @param {object}  form              – { description, amount, category, date, paid_by, split_method }
 * @param {object}  opts
 * @param {boolean} opts.isCustomCategory – whether a custom category is being used
 * @param {string}  opts.customCategory   – the custom category text
 * @param {string}  opts.today            – today's date as ISO string (YYYY-MM-DD)
 * @returns {string|null} error message, or null if valid
 */
export function validateExpense(form, { isCustomCategory = false, customCategory = "", today } = {}) {
  if (!form.description.trim()) {
    return "Description is required.";
  }

  const effectiveCategory = isCustomCategory
    ? customCategory.trim()
    : form.category;

  if (!effectiveCategory) {
    return "Category is required.";
  }

  if (isCustomCategory) {
    // Case-insensitive collision check, mirroring the backend guard — a
    // custom category matching an existing one (e.g. "groceries" vs
    // "Groceries") would otherwise fragment analytics into a second bucket,
    // or silently collide with a reserved category's money-math semantics.
    const collision = CATEGORIES.find(
      (c) => c.toLowerCase() === effectiveCategory.toLowerCase()
    );
    if (collision && collision !== effectiveCategory) {
      return `'${collision}' already exists — select it from the category list.`;
    }
  }

  const amt = parseFloat(form.amount);
  if (!form.amount || amt === 0) {
    return "Amount cannot be zero.";
  }
  if (amt < 0 && effectiveCategory !== "Reimbursement") {
    return "Negative amounts are only allowed for Reimbursement.";
  }
  if (amt > 0 || effectiveCategory === "Reimbursement") {
    // valid — skip the redundant check
  } else {
    return "Amount must be greater than 0.";
  }

  if (form.date > today) {
    return "Date cannot be in the future.";
  }

  if (form.split_method === `100% ${form.paid_by}`) {
    return "Split method cannot assign 100% to the person who paid.";
  }

  return null;
}
