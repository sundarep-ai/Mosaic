# Mosaic Features

Full reference for all features across every page and mode.

---

## Insights

Automated analysis of your spending patterns, on its own dedicated page. All monetary values reflect your personal expense share, not raw totals.

The page is **attention-first**: a single headline, a "Needs your attention" tier for actionable signals, and a "Trends & patterns" tier for the always-on analysis. Sections that have no data for your account are hidden rather than shown as empty placeholders — a brand-new account sees a single friendly empty state, not a wall of blank boxes. Insights no longer appear on the Home page.

### On-Pace Headline

A one-line current-month projection — *"On track for ~$X this month"* — combining what you've already spent this month, scheduled bills still due before month-end, and your typical variable spending rate.

### Alert Banners (Needs your attention)

- **Price-increase alerts** — detects when a recurring bill steps up (or down) to a new price and tells you the story: *"Netflix $15.99 → $17.99 since March · +$24/yr"*, showing the old price, new price, the date it changed, and the annualized impact. Stays visible until the new price is confirmed a few times, then goes quiet.
- **New-subscription alerts** — flags a brand-new recurring charge as early as its second occurrence (*"Disney+ looks like a new monthly subscription"*), so a signup you forgot about surfaces quickly.
- **Category trend alerts** — flags categories tracking above or below your usual spending, compared fairly against your spend *through the same day of the month* in prior months (so a partial month isn't misread as "down 60%"). Suppressed when the increase is already explained by an anomaly or a price step, to avoid three alerts for one cause.
- **Dismiss** — alerts can be dismissed; a dismissed alert stays gone until the situation changes (e.g. the price steps again).

### Forecast

Predicts next month's spending as **scheduled bills + variable spending**:

- **Scheduled** — each detected recurring bill projected into the month(s) it's actually due (an annual bill appears only in its due month, not smeared across the year).
- **Variable** — the median of your recent complete months' non-recurring spend, with a seasonal adjustment once there's enough history (13+ months).
- A **likely range** (not just a single number) once there's enough history, a per-category comparison vs. last month, and the percentage change from the previous month.
- **Upcoming bills** — the next due dates across your recurring charges.
- **Subscription roll-up** — how many active recurring charges you have and their combined monthly and annual cost (*"12 active recurring ≈ $214/mo ≈ $2,568/yr"*).

### Unusual Expenses (Anomalies)

Cards highlighting individual expenses that are genuinely unusual for their category, using robust statistics (median/MAD) that aren't thrown off by one big outlier. Only unusually *high* expenses are surfaced. Shows the expense description, amount, the category's usual value, and date.

### Recurring Expenses

A table of detected recurring expenses: description, category, detected frequency (Weekly, Biweekly, Monthly, Bimonthly, Quarterly, Semiannual, Annual), average amount, last amount, and total occurrences. Detection handles skipped cycles and same-day duplicate postings, and covers cadences that a simpler detector would miss (bimonthly, semiannual). Sorted by occurrence count.

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

Available when Income Tracking is enabled. A Sankey diagram showing income sources (left) flowing into expense categories (right). If income exceeds expenses, a Savings node appears on the right; if you spent more than you earned, a red callout states the deficit explicitly (*"You spent $X more than you earned this period"*) instead of quietly showing no savings. Up to 8 expense categories are shown; the rest are bucketed as "Other Expenses". The chart respects the active date range filter.

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
- **Category** — choose from the default list or create your own with `+ New Category`. A custom name is accepted as long as it isn't an empty/whitespace-only string and doesn't collide (case-insensitively) with an existing category — so you can't accidentally create a second `groceries` alongside `Groceries` and split your analytics in two.

  Default categories: Groceries, Rent, Utilities, Dining, Transportation, Entertainment, Healthcare, Shopping, Travel, Payment, Gas, Car Insurance, Car Maintenance, Home Care, Pet Care, Pet Insurance, Vet, Gift, Subscription, Parking, Tenant Insurance, Reimbursement, Other.

- **Who Paid** (Shared / Blended) — which partner paid.
- **Split Method** (Shared / Blended) — how to divide the expense:
  - `50/50` — split equally; the non-payer owes half.
  - `100% (Other Owes)` — the non-payer is fully responsible.
  - `Personal` — no balance impact; tracked privately for the payer only.
- **Live split preview** (Shared / Blended) — a sentence under the amount shows the net effect on your balance as you type, e.g. *"50/50 → you'll owe Bob $12.50"* or *"100% → Bob will owe you $100.00"*, so you can see who ends up owing what before saving.

#### Split Calculator (Shared / Blended)

For a mixed receipt — some items only yours, some only your partner's, some shared, some taxable — the **Split calculator** button works out the net amount owed in-app instead of forcing you to do the math offline. Add line items, mark each as Mine / Theirs / Shared and taxable or not, set a tax rate (remembered across sessions), and see a live *"X owes Y"* preview. "Use this result" fills the expense in as a `100% owes` entry with the computed amount.

#### Faster entry & crash safety

- **Save & add another** — save the current expense and immediately start a new one without leaving the page. The date, payer, and split method are kept (usually the same across a batch of receipts); the description, amount, and category reset.
- **Half-typed entries survive** — switching between the Expense and Income tabs keeps whatever you'd started typing in each. If your session expires while saving, Mosaic stashes the in-progress entry and offers to **Restore** it after you log back in, so a timeout never eats your data.
- **Clear error messages** — validation problems from the server (e.g. an invalid split for a settlement) are shown directly instead of a generic failure.

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

**Shareable filters** — the active search and filters are reflected in the page URL, so a filtered view can be bookmarked or shared, and it's restored when you come back. Either partner can edit either person's expense, and editing a row returns you to the exact filtered view you came from instead of a blank list.

**Edit** — click the pencil icon to edit any expense's details inline.

**Delete** — click the trash icon to permanently delete an expense (with confirmation dialog).

**Pagination** — 100 expenses load at a time; a "Load 100 more" button in the footer reaches the rest, all the way back to your oldest entries.

**Drill-down from Calendar / Analytics** — clicking a day in the Calendar or a point in the Spending Velocity chart lands you here pre-filtered to that date or month (and optionally category). A filter pill labels the active drill-down and where it came from; click × to clear it.

**Clean Up badge** — when there are description duplicates to review, the Clean Up button shows a count so you know there's something to tidy without opening it.

**Export** — download the current filtered view as a `.xlsx` spreadsheet. The export matches exactly what's on screen — the same search, category, payer, date range, type, and sort — and includes a second **Income** sheet alongside the expenses.

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

**Currency selector** — switch the display currency symbol: USD, EUR, GBP, CAD, AUD, INR, JPY, CNY, CHF, SGD. Display-only — amounts are not converted. Your choice is saved to your account, so it follows you across devices and browsers. Amounts display with thousands separators and a correctly-placed negative sign.

**Dark / Light mode** — toggle between themes. Preference is saved in localStorage.

**Mobile bottom navigation** — on mobile, a bottom nav bar provides quick access to Home, Add New, Analytics, Calendar, Insights, and Expenses.

**Toast notifications** — saves, deletes, merges, and errors surface as brief, auto-dismissing toasts that persist across page navigation, replacing blocking browser alert dialogs.

---

## Data Protection

### Audit Log

Every mutation (create, update, delete, description merge) is appended to `backend/data/audit/audit.jsonl` as a permanent, append-only record. Each entry captures the timestamp, operation type, user, and full before/after data — a complete reconstruction history even if the database is lost.

### Automatic Backups

Mosaic creates timestamped backups of both the database and the audit log — on startup and again periodically as your data changes, so a long-running install stays current. Each backup is **verified after it's written** (integrity check plus a row-count comparison against the live data) so a silently-corrupt backup isn't mistaken for a good one. Backups are stored in `backend/data/backups/` and rotated to keep the most recent (30 by default, configurable). For off-site redundancy, set `BACKUP_PATH` in `backend/.env` to a cloud-synced folder:

```env
BACKUP_PATH=C:/Users/yourname/OneDrive/Mosaic-Backups
```

Backups use the SQLite online backup API — safe to create while the app is running. On startup, Mosaic checks the database's integrity and refuses to start on a corrupt file (naming the backup folder to restore from) rather than backing up over a good copy.

### Security

- Passwords and security answers are stored as bcrypt hashes — plaintext is never stored.
- Session cookies are HMAC-SHA256 signed with a required `SECRET_KEY`.
- Changing your password invalidates all existing sessions immediately.
- Sessions slide forward with activity — an active session no longer logs you out mid-use at a fixed cutoff (opt into a year-long session with "Stay Signed In").
- Forgot-password resets are rate-limited to 5 attempts per 5-minute window per username.
- Avatar uploads are validated with magic byte checks and path traversal protection; file writes are atomic. Static file serving is guarded against directory-traversal escapes.
- Personal mode blocks the second user at the auth layer, not just in the UI; only the primary account holder can switch the app back to Personal mode.
- Account creation is capped at 2 users, enforced server-side.
- Account deletion requires password confirmation.
