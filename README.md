<div align="center">

# MosaicTally

**A flexible, local-first expense tracker — solo, shared, or both.**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-3.4-06B6D4?logo=tailwindcss&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

</div>

---

MosaicTally tracks expenses — personal, shared between two people, or both — calculates who owes whom, and provides visual analytics. Everything runs locally with zero cloud dependencies. Choose from three modes to match how you want to track spending:

| Mode | Description |
|---|---|
| **Solo** | Single-user personal expense tracking. No balance, no split options, simplified UI. |
| **Shared** (default) | Two-person shared expenses with balance tracking, split methods, and settle-up. |
| **Personal + Shared** (Hybrid) | Both personal and shared expenses — see your own spending alongside what you split. |

Switch modes anytime from the Settings page (gear icon in the top bar). Mode changes only affect validation and UI — your data is never deleted or migrated.

### How "Your Expense" Is Calculated

Across Home, Analytics, and Calendar, MosaicTally shows each user their personal expense burden — not the raw total of all expenses. The calculation depends on the split method:

| Split Method | Your Portion |
|---|---|
| **Personal** (paid by you) | 100% of the amount |
| **Personal** (paid by partner) | 0% |
| **50/50** | 50% of the amount (regardless of who paid) |
| **100% You** | 100% of the amount (you owe it all) |
| **100% Partner** | 0% (they owe it all) |

In **Solo** mode, all expenses are Personal, so your expense equals the total. In **Shared** mode, your expense is your portion of all shared expenses. In **Hybrid** mode, it combines your personal expenses plus your portion of shared ones.

Reimbursements (stored as negative amounts) reduce your net expense on Home and Analytics but are excluded from Calendar day totals to avoid confusion when a reimbursement arrives in a different month than the original expense.

## Features

| Page | What it does |
|---|---|
| **Home** | Mode-aware overview with "Your Expense This Month" — your personal portion of all spending. **Solo** shows your total; **Shared** / **Hybrid** add a balance card and settle button alongside your expense card. All modes show this month's spend by category and recent activity. |
| **Add Expense** | Log an expense with date, description, category, amount, payer, and split method. In Solo mode, the "Who Paid" and "Split Method" fields are hidden (defaults to the single user and "Personal"). Supports custom categories via "+ New Category". Fuzzy matching suggests existing descriptions and auto-suggests categories — all client-side. |
| **Settings** | Choose your app mode (Solo / Shared / Personal + Shared) and upload a profile picture. Accessible via the gear icon in the top bar. |
| **Edit Expense** | Full-page edit form at `/edit/:id` — reuses the Add Expense form with all fields pre-filled |
| **Analytics** | Date-range filtered Bar / Pie / Line charts, summary cards, top 5 largest expenses. Filter presets: 1M, 3M, 6M, YTD, 1Y, All — plus custom date range. **Solo** shows your total expense; **Shared** / **Hybrid** show total shared spend, your share, and total spend. Payer breakdown hidden in Solo; Personal vs Shared chart shown in Hybrid. |
| **Calendar** | Month-view calendar showing your daily expense portion with logarithmic heat-map shading (prevents a single outlier like rent from washing out all other days). Navigate months with chevron arrows or jump to any month/year via a dropdown picker. Displays your monthly expense at the top alongside total shared spend (in Shared/Hybrid modes). Day cells show only your portion. Click any day to drill down into that day's expenses on the History page. Payment and Reimbursement categories are excluded from calendar totals. |
| **Smart Insights** | Automated spending analysis — detects recurring payments (weekly/monthly/quarterly/annual) with change alerts, highlights category trend spikes, flags statistical anomalies, projects next-month spending via weighted moving average, compares weekend vs weekday habits, and ranks fastest-growing categories. All computed server-side using rule-based pattern detection and the existing embedding model for description clustering. |
| **History** | Full expense table with search, category & payer filters, edit (navigates to edit page), delete with confirmation. In Solo mode, the "Paid By" column and filter are hidden. In Hybrid mode, an extra "Type" filter lets you toggle between All, Personal, and Shared expenses. Includes a "Clean Up" tool that uses AI embeddings to find and merge similar description variants (e.g. "Foodbasics" / "Food Basics"). |
| **Export** | Download the current filtered view as an `.xlsx` file |

### Currency Selector

A currency dropdown in the top navigation bar lets you choose your display currency. The selection is persisted in localStorage and applies across all pages instantly. Supported currencies: USD, EUR, GBP, CAD, AUD, INR, JPY, CNY, CHF, SGD.

### Profile Pictures

Each user can upload a profile picture from the Settings page (gear icon → Profile Picture → Change Photo). Avatars appear on the Home page (balance card) and in the History table's "Paid By" column. Images are stored locally in `backend/uploads/avatars/` (created automatically on first server start, gitignored). Accepted formats: JPG, PNG, GIF, WebP — max 2 MB. Uploads are validated against magic bytes to ensure file content matches the declared type.

### Split Methods

| Method | Availability | Behaviour |
|---|---|---|
| `50/50` | Shared, Hybrid | Cost is shared equally — the non-payer owes half |
| `100% (Other Owes)` | Shared, Hybrid | The non-payer is fully responsible for the expense |
| `Personal` | All modes | No balance impact — a personal expense logged for tracking only. In Solo mode, this is the only option (applied automatically). |

### Validation

- **Amount** must be greater than zero (enforced on both frontend and backend) and is automatically rounded to 2 decimal places on input
- **Date** cannot be in the future (enforced on both frontend and backend)
- **Paid By** and **Split Method** are validated dynamically based on the current app mode — Solo restricts to a single user and "Personal" split only
- **Category** is free-form — choose from the default list or create a custom category

## Data Protection

MosaicTally protects your expense data in two ways:

### Audit Log

Every mutation (create, update, delete, description merge) is appended to `backend/data/audit/audit.jsonl` as a permanent, never-truncated record. Each line captures the timestamp, operation type, user, and full before/after data — giving you a complete reconstruction history even if the database is lost.

### Automatic Backups

On every startup, the app creates a timestamped backup of both the database and the audit log. Backups are stored in `backend/data/backups/` by default and rotated to keep the 10 most recent. For cloud redundancy, set `BACKUP_PATH` in `backend/.env` to a OneDrive (or any synced) folder:

```env
BACKUP_PATH=C:/Users/yourname/OneDrive/MosaicTally-Backups
```

Backups use the SQLite online backup API — consistent snapshots safe to create while the app is running.

### SQLite Hardening

The database runs in WAL (Write-Ahead Logging) mode for crash recovery, and an integrity check runs on every startup to detect corruption early. Indexes on `date`, `category`, and `paid_by` are created automatically on startup for faster queries.

### Security

- **Passwords** are stored as bcrypt hashes in `backend/.env` — plaintext passwords are never stored
- **Session cookies** are HMAC-SHA256 signed with a required `SECRET_KEY` — the app refuses to start without one
- **Avatar uploads** are validated with magic byte checks and path traversal protection
- **Solo mode** blocks login for the second user at the auth layer — not just hidden in UI
- **Search queries** escape SQL LIKE wildcards to prevent injection

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
cd MosaicTally
```

### 2. Configure users

Copy the example config and edit it with your own names:

```bash
cd backend
cp config.example.py config.py
```

Edit **`backend/config.py`** — the frontend fetches names automatically from the backend at runtime:

```python
# Display names shown in the UI
USER_A = "Alice"
USER_B = "Bob"

# Login usernames (used for authentication)
USER_A_LOGIN = "alice"
USER_B_LOGIN = "bob"
```

> **Note:** `config.py` is gitignored. Use `config.example.py` as your starting template.

Then create **`backend/.env`** for passwords and the session secret (see `.env.example`):

```env
USER_A_PASSWORD=<bcrypt hash>
USER_B_PASSWORD=<bcrypt hash>
SECRET_KEY=<long random string>

# Optional: set to a OneDrive/cloud folder for cloud-synced backups
# BACKUP_PATH=C:/Users/yourname/OneDrive/MosaicTally-Backups
```

**Passwords must be bcrypt hashes**, not plaintext. Generate them after installing dependencies (step 3):

```bash
cd backend
python -c "from auth import hash_password; print(hash_password('your-password'))"
```

**SECRET_KEY** is required — the app will refuse to start without one. Generate a strong key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

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
The SQLite database (`tallyus.db`) is created automatically on first run.

> **Tip:** Interactive API docs are available at http://localhost:8000/docs (Swagger UI).

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

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
| Paid By | Must match `USER_A` / `USER_B` display names in `backend/config.py` |
| Split Method | 50/50, 100% \<User A name\>, 100% \<User B name\>, Personal |

## API Reference

All endpoints are prefixed with `/api`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/expenses` | List expenses (query: `search`, `paid_by`, `category`, `limit`, `sort`) |
| `POST` | `/expenses` | Create a new expense |
| `GET` | `/expenses/{id}` | Get a single expense |
| `PUT` | `/expenses/{id}` | Update an expense |
| `DELETE` | `/expenses/{id}` | Delete an expense |
| `GET` | `/suggest-category` | Auto-suggest a category from history (query: `description`) |
| `GET` | `/unique-descriptions` | All unique (description, category, count) tuples for client-side fuzzy matching |
| `GET` | `/similar-descriptions` | Embedding-based similarity clusters grouped by category (query: `threshold`) |
| `POST` | `/merge-descriptions` | Merge variant descriptions into a canonical form within a category |
| `GET` | `/balance` | Current balance between the two configured users |
| `GET` | `/monthly-summary` | Category totals for the current month |
| `GET` | `/analytics` | Aggregated analytics including `my_share` (query: `start_date`, `end_date`) |
| `GET` | `/insights` | Smart insights: recurring payments, trend alerts, anomalies, forecast, weekend vs weekday, top growing categories |
| `GET` | `/personal-summary` | Current user's personal spend for this month (Hybrid mode) |
| `GET` | `/my-expense-summary` | Current user's total expense portion and total shared spend for this month |
| `GET` | `/settings` | Current app mode |
| `PUT` | `/settings` | Update app mode (`solo`, `duo`, `hybrid`) |
| `GET` | `/export` | Download filtered expenses as `.xlsx` (query: `search`, `paid_by`, `category`) |

## Project Structure

```
backend/
  config.example.py      # Template — copy to config.py and edit with your names
  config.py              # Your local config (gitignored)
  .env                   # Passwords & session secret (not committed — see .env.example)
  main.py                # FastAPI app & CORS config
  database.py            # SQLite engine (WAL mode), session provider, integrity check
  models.py              # Expense & Settings tables, Pydantic schemas
  migrate_xlsx.py        # Bulk import from .xlsx
  requirements.txt       # Python dependencies
  services/
    audit.py             # Append-only JSONL audit logger
    backup.py            # Startup backup manager (SQLite online backup API)
    clustering.py        # Shared embedding model & cosine-similarity clustering
  routes/
    expenses.py          # CRUD, balance, monthly summary, description similarity & merge
    analytics.py         # Date-filtered analytics aggregation
    insights.py          # Smart insights: recurring detection, trends, anomalies, forecast
    export.py            # .xlsx file generation & download
  data/                  # Generated at runtime (gitignored)
    audit/
      audit.jsonl        # Permanent append-only audit log of all mutations
    backups/             # Timestamped DB + audit log snapshots (or see BACKUP_PATH)

frontend/
  package.json           # Node dependencies & scripts
  vite.config.js         # Vite configuration (includes dev API proxy)
  tailwind.config.js     # Tailwind content paths & custom theme
  index.html             # HTML entry point
  src/
    config.js            # API base URL & app name (user names fetched from backend)
    main.jsx             # React root & router setup
    App.jsx              # Route definitions & layout shell (includes /edit/:id, /settings)
    ConfigContext.jsx     # User names, app mode, and setMode — fetched from backend
    CurrencyContext.jsx  # Currency selection context with localStorage persistence
    ErrorBoundary.jsx    # Catches render errors to prevent white-screen crashes
    index.css            # Tailwind directives
    api/
      fetchWithAuth.js   # Centralized fetch wrapper with automatic 401 → logout handling
      expenses.js        # Fetch helpers for all endpoints
    constants/
      categories.js      # Shared category list, icons, and color mappings
    hooks/
      useDescriptionSuggestions.js  # Fuse.js-powered fuzzy matching for descriptions & categories
    components/
      Navbar.jsx                   # Sticky navigation bar
      MergeDescriptionsModal.jsx   # Bulk description merge review UI
    pages/
      Landing.jsx        # Dashboard page
      AddExpense.jsx     # New/edit expense form (also handles /edit/:id)
      Analytics.jsx      # Charts & analytics dashboard
      Calendar.jsx       # Month-view calendar with daily spend totals and month/year picker
      Insights.jsx       # Smart Insights: recurring payments, trends, anomalies, forecast
      Settings.jsx       # App mode selector & profile picture upload
      History.jsx        # Expense table with delete/export, edit navigates to /edit/:id
```

## License

This project is licensed under the [MIT License](LICENSE).
