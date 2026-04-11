<div align="center">

# Mosaic

**A flexible, local-first expense tracker — solo, shared, or both.**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-3.4-06B6D4?logo=tailwindcss&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

</div>

---

Mosaic tracks expenses — personal, shared between two people, or both — calculates who owes whom, and provides visual analytics. Everything runs locally with zero cloud dependencies. Choose from three modes to match how you want to track spending:

| Mode | Description | Income Tracking |
|---|---|---|
| **Personal** | Single-user personal expense tracking. No balance, no split options, simplified UI. | Available (opt-in) |
| **Shared** (default) | Two-person shared expenses with balance tracking, split methods, and settle-up. | Not available — incomplete picture of each person's finances |
| **Blended** | Both personal and shared expenses — see your own spending alongside what you split. | Available (opt-in, per user) |

Switch modes anytime from the Settings page (gear icon in the top bar). Mode changes only affect validation and UI — your data is never deleted or migrated.

### How "Your Expense" Is Calculated

Across Home, Analytics, Calendar, and Smart Insights, Mosaic shows each user their personal expense burden — not the raw total of all expenses. The calculation depends on the split method:

| Split Method | Your Portion |
|---|---|
| **Personal** (paid by you) | 100% of the amount |
| **Personal** (paid by partner) | 0% |
| **50/50** | 50% of the amount (regardless of who paid) |
| **100% You** | 100% of the amount (you owe it all) |
| **100% Partner** | 0% (they owe it all) |

In **Personal** mode, all expenses are Personal, so your expense equals the total. In **Shared** mode, your expense is your portion of all shared expenses. In **Blended** mode, it combines your personal expenses plus your portion of shared ones.

Reimbursements (stored as negative amounts) reduce your net expense on Home and Analytics but are excluded from Calendar day totals to avoid confusion when a reimbursement arrives in a different month than the original expense.

## Features

| Page | What it does |
|---|---|
| **Home** | Mode-aware overview with "Your Expense This Month" — your personal portion of all spending. **Personal** shows your total; **Shared** / **Blended** add a balance card and settle button alongside your expense card. When Income Tracking is enabled, a third tile shows "Income This Month" and the Spend by Category section moves below. All modes show this month's spend by category and recent activity. |
| **Add Expense** | Log an expense with date, description, category, amount, payer, and split method. In Personal mode, the "Who Paid" and "Split Method" fields are hidden (defaults to the single user and "Personal"). Supports custom categories via "+ New Category". Fuzzy matching suggests existing descriptions and auto-suggests categories — all client-side. |
| **Add Income** | Log income received at `/add-income`. Fields: date, amount, source (Salary / Wages, Freelance / Side Income, Other), optional notes. Available only when Income Tracking is enabled in Settings. |
| **Settings** | Choose your app mode (Personal / Shared / Blended), upload a profile picture, set your preferred date format, enable Income Tracking (Personal and Blended modes only), toggle Stay Signed In, change your password, and delete your account. |
| **Edit Expense** | Full-page edit form at `/edit/:id` — reuses the Add Expense form with all fields pre-filled |
| **Analytics** | Date-range filtered Bar / Pie / Line charts, summary cards, top 5 largest expenses. Filter presets: 1M, 3M, 6M, YTD, 1Y, All — plus custom date range. **Personal** shows your total expense; **Shared** / **Blended** show total shared spend, your share, and total spend. Payer breakdown hidden in Personal; Personal vs Shared chart shown in Blended. When Income Tracking is enabled, a **Sankey chart** appears at the top showing income sources → expense categories → Savings (if income exceeds expenses). |
| **Calendar** | Month-view calendar showing your daily expense portion with logarithmic heat-map shading (prevents a single outlier like rent from washing out all other days). Navigate months with chevron arrows or jump to any month/year via a dropdown picker. Displays your monthly expense at the top alongside total shared spend (in Shared/Blended modes). Day cells show only your portion. Click any day to drill down into that day's expenses on the History page. Payment and Reimbursement categories are excluded from calendar totals. When Income Tracking is enabled, days with income show a green `+` badge and the income amount alongside the expense amount. |
| **Smart Insights** | User-portion-aware spending analysis — all monetary values reflect **your expense** (your share based on split method), not raw totals. Detects recurring payments (weekly/monthly/quarterly/annual) with change alerts, highlights category trend spikes, flags statistical anomalies, projects next-month spending via weighted moving average, and ranks fastest-growing categories. **Weekend vs Weekday** shows side-by-side panels comparing your expense and shared expense patterns. In non-Personal modes, shared (full) amounts are shown as secondary info alongside your portion. When **Income Tracking** is enabled (Personal/Blended), an additional section shows savings rate, income vs expenses trend, and income breakdown by source. All computed server-side. |
| **History** | Full expense table with search, category & payer filters, edit (navigates to edit page), delete with confirmation. In Personal mode, the "Paid By" column and filter are hidden. In Blended mode, an extra "Type" filter lets you toggle between All, Personal, and Shared expenses. Includes a "Clean Up" tool that uses AI embeddings to find and merge similar description variants (e.g. "Foodbasics" / "Food Basics") — with Accept, Reject, and Review Later actions per suggestion, a Custom Merge tab for manual merges, and a Dismissed tab to restore accidentally rejected pairs. |
| **Export** | Download the current filtered view as an `.xlsx` file |

### Account Management

User accounts are stored in the SQLite database (no hardcoded config files). The app supports up to 2 accounts.

| Feature | Description |
|---|---|
| **Create Account** | Available from the login page when fewer than 2 accounts exist. Collects display name, username, password, and a security question + answer. |
| **Forgot Password** | Security question-based password reset accessible from the login page. Enter your username, answer your security question, then set a new password. |
| **Change Password** | Available in Settings under the Security section. Requires your current password. |
| **Stay Signed In** | Per-user toggle in Settings. When enabled, your session lasts 1 year instead of 8 hours. Convenient for locally hosted apps. |
| **Delete Account** | In Settings under the Danger Zone. Requires your password. Choose to delete all your data or anonymize it (expenses show as "Deleted User"). |
| **CLI Password Reset** | Last-resort recovery when you can't answer your security question. Run `python cli_reset_password.py` on the host machine — requires physical/SSH access. |

### Income Tracking

Income Tracking is an optional opt-in feature available in **Personal** and **Blended** modes. It is not available in Shared mode because that mode only reflects shared household expenses — without a complete view of each person's personal finances, an income-vs-expenses picture would be misleading.

**To enable:** Go to Settings → toggle "Enable Income Tracking". The setting is stored per browser (localStorage) and per user, so each user can opt in independently.

**How it works:**

- Log income at `/add-income` (linked from the Home income tile or via the Add Income button)
- Income sources: **Salary / Wages**, **Freelance / Side Income**, **Other**
- Income is private — in Blended mode, your income is never visible to the other user
- In the **Analytics** page, a Sankey chart visualises how income flows into expense categories. If income exceeds expenses, the remainder is shown as a **Savings** node. The chart respects the active date range filter.
- On the **Home** page, an "Income This Month" tile shows the current month's total and source breakdown
- On the **Calendar** page, days with income logged show a green `+` badge and the income amount

**Mode switching safety:** Switching to Shared mode from Settings automatically clears the Income Tracking opt-in. The backend also rejects income API requests with `403` if the current mode is `duo`.

### Currency Selector

A currency dropdown in the top navigation bar lets you choose your display currency. The selection is persisted in localStorage and applies across all pages instantly. Supported currencies: USD, EUR, GBP, CAD, AUD, INR, JPY, CNY, CHF, SGD.

### Date Format

Each user can choose their preferred date display and input format from the Settings page. The setting is stored per user in the database (not localStorage), so it follows you across browsers.

| Format | Example |
|---|---|
| DD/MM/YYYY (default) | 25/12/2025 |
| MM/DD/YYYY | 12/25/2025 |
| YYYY/MM/DD | 2025/12/25 |
| YYYY/DD/MM | 2025/25/12 |

The chosen format applies everywhere dates appear (Home, History, Analytics, Calendar, Insights) and everywhere dates are entered (Add Expense, Add Income, Analytics custom date range). Date inputs use a custom text field with auto-slash insertion and format-aware placeholder — replacing the native browser date picker so the format is consistent regardless of OS locale. Database storage always remains ISO `YYYY-MM-DD`.

### Description Clean Up

The History page includes a "Clean Up" button that uses AI embeddings (fastembed / ONNX) to find description variants that likely refer to the same thing (e.g. "Foodbasics" vs "Food Basics"). The merge review modal offers three workflows:

- **Suggestions tab** — AI-detected clusters. Each group can be Accepted (merges immediately into the canonical form), Rejected (permanently dismissed), or skipped for later review. Immediate toast feedback after each action.
- **Custom Merge tab** — Manual merge with autocomplete from existing descriptions, category picker, source description list builder, and a live preview of what will change.
- **Dismissed tab** — Lists all previously rejected pairs grouped by category, with a Restore button to undo accidental rejects.

Dismissed pairs are stored in a `DismissedMerge` table using canonical alphabetical ordering, so dismissing A↔B and B↔A are treated as the same pair. Dismissed pairs are automatically filtered out of future AI suggestions.

### Profile Pictures

Each user can upload a profile picture from the Settings page (gear icon → Profile Picture → Change Photo). Avatars appear on the Home page (balance card) and in the History table's "Paid By" column. Images are stored locally in `backend/uploads/avatars/` (created automatically on first server start, gitignored). Accepted formats: JPG, PNG, GIF, WebP — max 2 MB. Uploads are validated against magic bytes to ensure file content matches the declared type.

### Split Methods

| Method | Availability | Behaviour |
|---|---|---|
| `50/50` | Shared, Blended | Cost is shared equally — the non-payer owes half |
| `100% (Other Owes)` | Shared, Blended | The non-payer is fully responsible for the expense |
| `Personal` | All modes | No balance impact — a personal expense logged for tracking only. In Personal mode, this is the only option (applied automatically). |

### Validation

- **Amount** must be greater than zero (enforced on both frontend and backend) and is automatically rounded to 2 decimal places on input
- **Date** cannot be in the future (enforced on both frontend and backend)
- **Paid By** and **Split Method** are validated dynamically based on the current app mode — Personal restricts to a single user and "Personal" split only
- **Category** is free-form — choose from the default list or create a custom category

## Data Protection

Mosaic protects your expense data in two ways:

### Audit Log

Every mutation (create, update, delete, description merge) is appended to `backend/data/audit/audit.jsonl` as a permanent, never-truncated record. Each line captures the timestamp, operation type, user, and full before/after data — giving you a complete reconstruction history even if the database is lost.

### Automatic Backups

On every startup, the app creates a timestamped backup of both the database and the audit log. Backups are stored in `backend/data/backups/` by default and rotated to keep the 10 most recent. For cloud redundancy, set `BACKUP_PATH` in `backend/.env` to a OneDrive (or any synced) folder:

```env
BACKUP_PATH=C:/Users/yourname/OneDrive/Mosaic-Backups
```

Backups use the SQLite online backup API — consistent snapshots safe to create while the app is running.

### SQLite Hardening

The database runs in WAL (Write-Ahead Logging) mode for crash recovery, and an integrity check runs on every startup to detect corruption early. Indexes on `date`, `category`, and `paid_by` are created automatically on startup for faster queries.

### Security

- **Passwords** are stored as bcrypt hashes in the database — plaintext passwords are never stored
- **Security answers** are normalized (lowercased, trimmed) and bcrypt-hashed before storage
- **Session cookies** are HMAC-SHA256 signed with a required `SECRET_KEY` — the app refuses to start without one
- **Avatar uploads** are validated with magic byte checks and path traversal protection
- **Personal mode** blocks login for the second user at the auth layer — not just hidden in UI
- **Search queries** escape SQL LIKE wildcards to prevent injection
- **Account creation** is capped at 2 users — enforced server-side with uniqueness constraints
- **Account deletion** requires password confirmation before proceeding

---

## Tech Stack

| Layer | Technologies |
|---|---|
| Backend | Python 3.10+, FastAPI, SQLModel, SQLite (WAL mode), openpyxl, fastembed (ONNX-based embeddings), bcrypt |
| Frontend | React 18 (Vite), Tailwind CSS 3, React Router 6, Recharts, Fuse.js (fuzzy search) |

## Prerequisites

- **Python 3.10+** &nbsp;—&nbsp; [python.org/downloads](https://www.python.org/downloads/)
- **Node.js 18+** &nbsp;—&nbsp; [nodejs.org](https://nodejs.org/)

## Getting Started

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd Mosaic
```

### 2. Configure the backend

Copy the example config:

```bash
cd backend
cp config.example.py config.py
```

Create **`backend/.env`** with your session secret:

```env
SECRET_KEY=<long random string>

# Optional: set to a OneDrive/cloud folder for cloud-synced backups
# BACKUP_PATH=C:/Users/yourname/OneDrive/Mosaic-Backups
```

**SECRET_KEY** is required — the app will refuse to start without one. Generate a strong key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> **Note:** User accounts are no longer configured in files. Create accounts through the web UI after starting the app.

### 3. Start the backend

```bash
cd backend
python -m venv venv

# Activate the virtual environment
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
uvicorn main:app --reload
```

The API will be available at **http://localhost:8000**.
The SQLite database (`mosaic.db`) is created automatically on first run.

> **Tip:** Interactive API docs are available at http://localhost:8000/docs (Swagger UI).

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser. On first visit you'll see the login page with a "Create Account" link — create up to 2 accounts through the web UI.

### 5. (Optional) Import existing data

If you have expenses in an `.xlsx` file:

```bash
cd backend
python migrate_xlsx.py path/to/expenses.xlsx
```

The script auto-detects columns by header keywords and supports multiple date formats (`YYYY-MM-DD`, `MM/DD/YYYY`, `DD/MM/YYYY`).

**Expected columns:**

| Column | Example values |
|---|---|
| Date | 2026-01-15 |
| Description | Weekly groceries |
| Amount | 45.50 |
| Category | Groceries, Rent, Utilities, Dining, etc. |
| Paid By | Must match a registered user's display name |
| Split Method | 50/50, 100% \<Display Name\>, Personal |

If you have income history in an `.xlsx` file (Personal / Blended mode only):

```bash
cd backend
python migrate_income_xlsx.py path/to/income.xlsx
```

**Expected columns:**

| Column | Required | Example values |
|---|---|---|
| Date | Yes | 2026-01-15 |
| Amount | Yes | 3500.00 |
| Source | Yes | Salary / Wages, Freelance / Side Income, Other |
| User ID | Yes | Must match a registered user's login username |
| Notes | No | Year-end bonus |

Rows with unrecognised sources, non-positive amounts, or unparseable dates are skipped with a warning — the rest are still imported.

### 6. (Optional) CLI password reset

If a user forgets their password and cannot answer their security question, reset it from the command line:

```bash
cd backend
python cli_reset_password.py
```

This requires direct access to the host machine (physical or SSH).

## API Reference

All endpoints are prefixed with `/api`.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | Public | Create a new account (max 2) |
| `GET` | `/auth/account-status` | Public | Check how many accounts exist |
| `GET` | `/auth/security-questions` | Public | List preset security questions |
| `POST` | `/auth/login` | Public | Log in with username/password |
| `POST` | `/auth/logout` | Auth | Log out (clear session cookie) |
| `GET` | `/auth/me` | Auth | Get current user info |
| `POST` | `/auth/forgot-password/question` | Public | Get security question for a username |
| `POST` | `/auth/forgot-password/reset` | Public | Reset password with security answer |
| `PUT` | `/auth/change-password` | Auth | Change password (requires current password) |
| `PUT` | `/auth/stay-signed-in` | Auth | Toggle stay-signed-in preference |
| `DELETE` | `/auth/account` | Auth | Delete account (with data action choice) |
| `POST` | `/auth/avatar` | Auth | Upload profile picture |
| `GET` | `/auth/avatar/{username}` | Auth | Get profile picture |
| `GET` | `/expenses` | Auth | List expenses (query: `search`, `paid_by`, `category`, `limit`, `sort`) |
| `POST` | `/expenses` | Auth | Create a new expense |
| `GET` | `/expenses/{id}` | Auth | Get a single expense |
| `PUT` | `/expenses/{id}` | Auth | Update an expense |
| `DELETE` | `/expenses/{id}` | Auth | Delete an expense |
| `GET` | `/suggest-category` | Auth | Auto-suggest a category from history (query: `description`) |
| `GET` | `/unique-descriptions` | Auth | All unique (description, category, count) tuples for client-side fuzzy matching |
| `GET` | `/similar-descriptions` | Auth | Embedding-based similarity clusters grouped by category, excluding dismissed pairs (query: `threshold`) |
| `POST` | `/merge-descriptions` | Auth | Merge variant descriptions into a canonical form within a category |
| `GET` | `/balance` | Auth | Current balance between the two users |
| `GET` | `/monthly-summary` | Auth | Category totals for the current month |
| `GET` | `/analytics` | Auth | Aggregated analytics including `my_share` (query: `start_date`, `end_date`) |
| `GET` | `/insights` | Auth | Smart insights: user-portion-aware recurring payments, trend alerts, anomalies, forecast, weekend vs weekday (dual view), top growing categories, income insights (Personal/Blended) |
| `GET` | `/personal-summary` | Auth | Current user's personal spend for this month (Blended mode) |
| `GET` | `/my-expense-summary` | Auth | Current user's total expense portion and total shared spend for this month |
| `GET` | `/config` | Public | Display names and app mode |
| `GET` | `/settings` | Public | Current app mode |
| `PUT` | `/settings` | Auth | Update app mode (`solo`, `duo`, `hybrid`) |
| `GET` | `/user-preferences` | Auth | Current user's preferences (date format) |
| `PUT` | `/user-preferences` | Auth | Update user preferences |
| `POST` | `/dismiss-merge` | Auth | Permanently dismiss a merge suggestion pair |
| `GET` | `/dismissed-merges` | Auth | List all dismissed merge pairs grouped by category |
| `POST` | `/undismiss-merge` | Auth | Restore a dismissed merge pair by ID |
| `GET` | `/export` | Auth | Download filtered expenses as `.xlsx` |
| `GET` | `/income` | Auth | List income entries (Personal/Blended only) |
| `POST` | `/income` | Auth | Create an income entry (Personal/Blended only) |
| `PUT` | `/income/{id}` | Auth | Update an income entry — owner only |
| `DELETE` | `/income/{id}` | Auth | Delete an income entry — owner only |
| `GET` | `/income/monthly-summary` | Auth | Total income and source breakdown for the current month |
| `POST` | `/income/sankey` | Auth | Income + expense breakdown for Sankey chart |

## Project Structure

```
backend/
  config.example.py      # Template — copy to config.py
  config.py              # Your local config (gitignored)
  .env                   # Session secret & backup path (not committed)
  main.py                # FastAPI app & CORS config
  database.py            # SQLite engine (WAL mode), session provider, integrity check
  models.py              # User, Expense, Income, Settings, UserPreference & DismissedMerge tables
  users.py               # Dynamic user resolution (replaces hardcoded config constants)
  auth.py                # Authentication, registration, password reset, account management
  cli_reset_password.py  # CLI tool for last-resort password reset
  migrate_xlsx.py        # Bulk import expenses from .xlsx
  migrate_income_xlsx.py # Bulk import income from .xlsx (Personal/Blended only)
  requirements.txt       # Python dependencies
  services/
    audit.py             # Append-only JSONL audit logger
    backup.py            # Startup backup manager (SQLite online backup API)
    clustering.py        # Shared embedding model & cosine-similarity clustering
  routes/
    expenses.py          # CRUD, balance, monthly summary, description similarity & merge
    analytics.py         # Date-filtered analytics aggregation
    income.py            # Income CRUD, monthly summary, Sankey data (Personal/Blended only)
    insights.py          # Smart insights: recurring detection, trends, anomalies, forecast
    export.py            # .xlsx file generation & download

frontend/
  package.json           # Node dependencies & scripts
  vite.config.js         # Vite configuration (includes dev API proxy)
  tailwind.config.js     # Tailwind content paths & custom theme
  index.html             # HTML entry point
  src/
    config.js            # API base URL & app name (user names fetched from backend)
    main.jsx             # React root & router setup
    App.jsx              # Route definitions & layout shell
    ConfigContext.jsx     # User names, app mode, and setMode — fetched from backend
    CurrencyContext.jsx   # Currency selection context with localStorage persistence
    DateFormatContext.jsx # Per-user date format context with backend persistence
    ErrorBoundary.jsx    # Catches render errors to prevent white-screen crashes
    index.css            # Tailwind directives
    auth/
      AuthContext.jsx    # Authentication state, login/logout, 401 handling
    api/
      fetchWithAuth.js   # Centralized fetch wrapper with automatic 401 → logout
      expenses.js        # Fetch helpers for all expense endpoints
      income.js          # Fetch helpers for income endpoints
    constants/
      categories.js      # Shared category list, icons, and color mappings
      incomeSources.js   # Income source constants
    hooks/
      useDescriptionSuggestions.js  # Fuse.js-powered fuzzy matching
      useIncomeMode.js   # localStorage-backed opt-in state for income tracking
    components/
      Navbar.jsx                   # Sticky navigation bar
      DateInput.jsx                # Format-aware date text input
      MergeDescriptionsModal.jsx   # Bulk description merge review UI
    pages/
      Landing.jsx        # Dashboard page
      Login.jsx          # Login page with Create Account and Forgot Password links
      CreateAccount.jsx  # Account registration with security question
      ForgotPassword.jsx # Security question-based password reset
      AddExpense.jsx     # New/edit expense form
      AddIncome.jsx      # Log income form (Personal/Blended only)
      Analytics.jsx      # Charts & analytics dashboard
      Calendar.jsx       # Month-view calendar with daily spend totals
      Insights.jsx       # Smart Insights page
      Settings.jsx       # App mode, profile picture, date format, stay signed in, change password, delete account
      History.jsx        # Expense table with delete/export and Clean Up
```

## License

This project is licensed under the [MIT License](LICENSE).
