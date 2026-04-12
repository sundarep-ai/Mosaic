# Mosaic Features

Full reference for all features across every page and mode.

---

## Insights

Automated analysis of your spending patterns. All monetary values reflect your personal expense share, not raw totals.

### Alert Banners

- **Recurring payment alerts** — flags when a recurring expense has changed significantly from its historical average, showing the old vs. new amount and the percentage change.
- **Category trend alerts** — flags categories where this month's spending is significantly above or below the 3-month average.

### Forecast

Predicts next month's total expense, broken down into recurring (predictable) and variable portions. Shows a per-category comparison of forecast vs. last month as a horizontal bar chart, plus the percentage change from the previous month. Requires at least 1 month of history.

### Unusual Expenses (Anomalies)

Cards highlighting individual expenses that are statistically unusual, much higher or lower than the category average. Shows the expense description, amount, category mean, and date.

### Recurring Expenses

A table of detected recurring expenses: description, category, detected frequency (Weekly, Biweekly, Monthly, Quarterly, Annual), average amount, last amount, and total occurrences. Sorted by occurrence count.

### Weekend vs Weekday Spending

Compares weekday and weekend spending: per-transaction averages, total counts, and weekend share percentage. A per-category bar chart shows the breakdown for the top 8 categories. In Shared / Blended mode, separate panels show "Your Expense" and "Shared Expense" side by side.

### Top Growing Categories

Lists categories with the highest month-over-month growth rate, showing the last 3 months of data. Requires at least 2 months of data.

### Income Insights

Available when Income Tracking is enabled (Personal / Blended modes).

- **Savings Rate** — current month's savings rate with income, expenses, and net savings. Color-coded: green for positive, red for negative.
- **Income by Source** — horizontal bar chart of this month's income by source.
- **Income vs Expenses** — bar chart of income and expenses per month with a surplus/deficit line.
- **Savings Rate Trend** — line chart of your savings rate over time.

---

## Description Clean Up

The History page includes a **Clean Up** button that uses AI embeddings (fastembed / ONNX) to find description variants that likely refer to the same thing — for example, "Foodbasics", "Food Basics", and "food basics". The model runs entirely on your device; no data is sent anywhere.

### Suggestions tab

AI-detected clusters of similar descriptions, grouped by category. For each group, choose a target name and click Accept to rename all variants immediately, or Reject to permanently dismiss that suggestion. Immediate toast feedback after each action.

### Custom Merge tab

Manually pick a category, enter a target description, and add source descriptions to rename. Includes autocomplete from existing descriptions and a live preview of what will change.

### Dismissed tab

Lists all previously rejected pairs grouped by category. Restore any accidentally rejected suggestion with a single click.

Dismissed pairs are stored with canonical alphabetical ordering (A↔B and B↔A are treated as the same pair) and are automatically excluded from future AI suggestions.

---

## Analytics

Date-range filtered charts and summaries of your spending.

### Date Range

Preset filters: **1M**, **3M**, **6M**, **YTD**, **1Y**, **All**. Or set a custom date range using the date inputs.

### Income Flow (Sankey Chart)

Available when Income Tracking is enabled. A Sankey diagram showing income sources (left) flowing into expense categories (right). If income exceeds expenses, a Savings node appears on the right. Up to 8 expense categories are shown; the rest are bucketed as "Other Expenses". The chart respects the active date range filter.

### Your Expense Summary

A summary card showing your total personal share of expenses for the selected period, plus the total shared spend and partner avatars (Shared / Blended).

### Category Distribution (Pie Chart)

A donut chart of your top 7 spending categories plus an Others bucket. Click any slice to drill down and see a horizontal bar chart of the top individual expenses within that category.

### Spending Velocity (Line Chart)

Monthly spending trend showing total spend and expense count per month. When drilled into a category, this chart updates to show that category's monthly trend. Click any data point to jump to the History page filtered to that month (and category, if drilled in).

### Payer Breakdown

How much each partner has paid and their percentage of total spend. Hidden in Personal mode.

### Personal vs Shared

Your spending divided into Personal and Shared portions with percentage bars. Shown in Blended mode.

### Largest Outlays

A table of your biggest individual expenses in the selected period: description, category, payer, date, and amount.

---

## Calendar

A monthly heat-map view of daily spending.

**Navigation** — left/right arrows to move between months. Click the month/year label to open a picker and jump to any month from 2000–2099.

**Heat-map shading** — each day cell's background intensity is scaled logarithmically based on your spending for that day relative to the month's range. This prevents a single large expense (like rent) from washing out all other days.

**Monthly Summary** — total personal expense for the displayed month, number of expenses, and total shared spend (Shared / Blended).

**Income badges** — when Income Tracking is enabled, days with income logged show a green `+` badge and the income amount alongside the expense total.

**Today** — highlighted with a ring for quick orientation.

**Click any day** to jump to the History page filtered to that specific date.

Payment-category expenses are excluded from calendar day totals. Reimbursements are included (their negative amounts reduce the day's total).

---

## Home (Dashboard)

Your financial snapshot for the current month.

**Current Balance** (Shared / Blended) — shows how much one partner owes the other based on shared expenses and payments. A zero balance means you're settled up. The **Settle** button logs a settlement payment to bring the balance back to zero.

**Your Expense This Month** — your personal share of all expenses this month. 50/50 splits count as half; Personal expenses count fully if you paid; 100% You expenses count fully regardless of who recorded them.

**Income This Month** — available when Income Tracking is enabled. Shows total income logged this month with a source breakdown (Salary, Freelance, Other).

**This Month's Spend by Category** — horizontal bar chart of your top 5 spending categories, sized relative to the largest.

**Recent Activity** — your last 5 expenses with description, category, date, amount, and (Shared / Blended) who paid.

---

## Modes

Mosaic supports three modes, switchable anytime from the Settings page. Mode changes affect validation and UI only — your data is never deleted or migrated.

### Personal

Single-user expense tracking. The "Who Paid" and "Split Method" fields are hidden — all expenses default to the logged-in user with a Personal split. No balance tracking. Income Tracking is available as an opt-in feature.

### Shared

Two-person expense tracking where every expense is split between both users. Tracks a running balance showing who owes whom, with a Settle Up button to log settlement payments. Income Tracking is not available in this mode — a shared-only view cannot accurately represent each person's full financial picture.

### Blended

Combines Personal and Shared tracking. Each expense can be personal (tracked privately) or shared (split and tracked in the balance). Each user sees their own expenses alongside the expenses they share with their partner. Income Tracking is available as an opt-in feature.

> Shared and Blended modes require a second registered account. A banner appears in the app when a second user registers, prompting you to switch modes.

### How "Your Expense" Is Calculated

Across the Home dashboard, Analytics, Calendar, and Insights, Mosaic shows each user their personal expense burden — not the raw total.

| Split Method | Your Portion |
|---|---|
| **Personal** (you paid) | 100% |
| **Personal** (partner paid) | 0% |
| **50/50** | 50% (regardless of who paid) |
| **100% You** | 100% |
| **100% Partner** | 0% |

---

## Add New

Two-tab form for logging expenses and income.

### Adding an Expense

- **Amount** — the total cost. Zero amounts are not allowed. Negative amounts are only permitted for the Reimbursement category (used to record money received back). Amounts are rounded to 2 decimal places automatically.
- **Date** — when the expense occurred, in your configured format. A calendar picker icon is available. Future dates are not allowed.
- **Description** — as you type, the app suggests matching descriptions from your history using fuzzy search (Fuse.js, client-side). Selecting a suggestion auto-fills the category field.
- **Auto-suggested category** — Mosaic suggests a category based on your past expenses for the same description. A sparkle indicator appears when a suggestion is active.
- **Category** — choose from the default list or create a custom category with `+ New Category`.

  Default categories: Groceries, Rent, Utilities, Dining, Transportation, Entertainment, Healthcare, Shopping, Travel, Payment, Gas, Car Insurance, Car Maintenance, Home Care, Pet Care, Pet Insurance, Vet, Gift, Subscription, Parking, Tenant Insurance, Reimbursement, Other.

- **Who Paid** (Shared / Blended) — which partner paid.
- **Split Method** (Shared / Blended) — how to divide the expense:
  - `50/50` — split equally; the non-payer owes half.
  - `100% (Other Owes)` — the non-payer is fully responsible.
  - `Personal` — no balance impact; tracked privately for the payer only.

### Adding Income

Available when Income Tracking is enabled.

- **Amount Received** — how much income was received.
- **Date** — when the income was received.
- **Source** — Salary / Wages, Freelance / Side Income, or Other.
- **Notes** — optional free-text (e.g. "March salary").

---

## History (Expenses)

A detailed, filterable list of all your expenses.

**Search** — type and press Enter to filter by description text.

**Filters:**
- Category — filter by any expense category.
- Paid By (Shared / Blended) — filter by which partner paid.
- Type (Blended only) — toggle between All, Personal, and Shared expenses.
- Amount — sort high to low or low to high.

**Expense table** — each row shows: date, description with category icon and badge, amount, and (Shared / Blended) who paid and the split type.

**Edit** — click the pencil icon to edit any expense's details inline.

**Delete** — click the trash icon to permanently delete an expense (with confirmation dialog).

Up to 100 expenses are shown at a time. The footer shows "Showing 100 of N expenses" when truncated — refine your filters to narrow the view.

**Drill-down from Analytics** — clicking a data point in the Spending Velocity chart lands you here with the month (and optionally category) pre-filtered. A filter pill shows the active filter; click × to clear it.

**Export** — download the current filtered view as a `.xlsx` spreadsheet.

---

## Settings

**Profile Picture** — upload a custom avatar (JPG, PNG, GIF, or WebP, max 2 MB). Avatars appear on the dashboard balance card and in the History table's "Paid By" column.

**Income Tracking** — toggle income tracking on or off. Available in Personal and Blended modes only. When enabled, unlocks the Add Income form, income tiles on the Home dashboard, the Sankey chart in Analytics, income badges on the Calendar, and Income Insights. Switching to Shared mode automatically disables income tracking.

**App Mode** — switch between Personal, Shared, and Blended.

**Date Format** — choose how dates are displayed and entered throughout the app. Stored per user in the database so it follows you across browsers.

| Format | Example |
|---|---|
| DD/MM/YYYY (default) | 25/12/2025 |
| MM/DD/YYYY | 12/25/2025 |
| YYYY/MM/DD | 2025/12/25 |
| YYYY/DD/MM | 2025/25/12 |

**Stay Signed In** — keep your session for up to a year instead of the default 8 hours.

**Change Password** — update your password by entering your current password and a new one (minimum 6 characters). All existing sessions are invalidated immediately.

**Delete Account** — permanently delete your account. Requires your password. Choose to anonymize your data (expenses show as "Deleted User") or delete everything.

---

## Account & Authentication

Mosaic supports up to 2 user accounts, created through the web UI.

**Create Account** — available from the login page when fewer than 2 accounts exist. Collects display name, username, password, and a security question and answer.

**Forgot Password** — reset your password by entering your username, answering your security question, and setting a new password. Rate-limited to 5 attempts per 5-minute window per username.

**CLI Password Reset** — last-resort recovery when you cannot answer your security question. Run `python cli_reset_password.py` on the host machine (requires direct or SSH access).

---

## Navigation & Toolbar

**Top navigation bar** — logo (links to Home), mode badge (Personal / Shared / Blended), page links, help icon, settings icon, user avatar, currency selector, dark/light mode toggle, logout.

**Currency selector** — switch the display currency symbol: USD, EUR, GBP, CAD, AUD, INR, JPY, CNY, CHF, SGD. Display-only — amounts are not converted.

**Dark / Light mode** — toggle between themes. Preference is saved in localStorage.

**Mobile bottom navigation** — on mobile, a bottom nav bar provides quick access to Home, Add New, Calendar, Insights, and Expenses.

---

## Data Protection

### Audit Log

Every mutation (create, update, delete, description merge) is appended to `backend/data/audit/audit.jsonl` as a permanent, append-only record. Each entry captures the timestamp, operation type, user, and full before/after data — a complete reconstruction history even if the database is lost.

### Automatic Backups

On every startup, Mosaic creates a timestamped backup of both the database and the audit log. Backups are stored in `backend/data/backups/` and rotated to keep the 10 most recent. For off-site redundancy, set `BACKUP_PATH` in `backend/.env` to a cloud-synced folder:

```env
BACKUP_PATH=C:/Users/yourname/OneDrive/Mosaic-Backups
```

Backups use the SQLite online backup API — safe to create while the app is running.

### Security

- Passwords and security answers are stored as bcrypt hashes — plaintext is never stored.
- Session cookies are HMAC-SHA256 signed with a required `SECRET_KEY`.
- Changing your password invalidates all existing sessions immediately.
- Forgot-password resets are rate-limited to 5 attempts per 5-minute window per username.
- Avatar uploads are validated with magic byte checks and path traversal protection; file writes are atomic.
- Personal mode blocks the second user at the auth layer, not just in the UI.
- Account creation is capped at 2 users, enforced server-side.
- Account deletion requires password confirmation.
