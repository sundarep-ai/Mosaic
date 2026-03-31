<div align="center">

# TallyUs

**A simple, local-first expense tracker for two people.**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-3.4-06B6D4?logo=tailwindcss&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

</div>

---

TallyUs tracks shared expenses between two people, calculates who owes whom, and provides visual analytics — all running locally with zero cloud dependencies. User names are configured in a single place and flow through both the backend and frontend automatically.

## Features

| Page | What it does |
|---|---|
| **Dashboard** | Live balance (e.g. "User A owes User B $50"), this month's spend by category, last 10 expenses. Includes a **Settle** button that opens the Add Expense form pre-filled with "Payment" description and category for quick balance settlements. |
| **Add Expense** | Log an expense with date, description, category, amount, payer, and split method. Supports custom categories via "+ New Category". As you type a description, fuzzy matching suggests existing descriptions ("Did you mean?") and instantly auto-suggests a category from history — all client-side with zero network latency. |
| **Edit Expense** | Full-page edit form at `/edit/:id` — reuses the Add Expense form with all fields pre-filled |
| **Analytics** | Date-range filtered Bar / Pie / Line charts, summary cards, top 5 largest expenses |
| **History** | Full expense table with search, category & payer filters, edit (navigates to edit page), delete with confirmation. Includes a "Clean Up" tool that uses AI embeddings to find and merge similar description variants (e.g. "Foodbasics" / "Food Basics"). |
| **Export** | Download the current filtered view as an `.xlsx` file |

### Profile Pictures

Each user can upload a profile picture by clicking their name in the top navigation bar. Avatars appear on the Dashboard (balance card) and in the History table's "Paid By" column. Images are stored locally in `backend/uploads/avatars/` (created automatically on first server start, gitignored). Accepted formats: JPG, PNG, GIF, WebP — max 2 MB. Uploads are validated against magic bytes to ensure file content matches the declared type.

### Split Methods

| Method | Behaviour |
|---|---|
| `50/50` | Cost is shared equally — the non-payer owes half |
| `100% (Other Owes)` | The non-payer is fully responsible for the expense |
| `Personal` | No balance impact — a personal expense logged for tracking only |

### Validation

- **Amount** must be greater than zero (enforced on both frontend and backend) and is automatically rounded to 2 decimal places on input
- **Date** cannot be in the future (enforced on both frontend and backend)
- **Paid By** and **Split Method** must match the configured user names
- **Category** is free-form — choose from the default list or create a custom category

## Data Protection

TallyUs protects your expense data in two ways:

### Audit Log

Every mutation (create, update, delete, description merge) is appended to `backend/data/audit/audit.jsonl` as a permanent, never-truncated record. Each line captures the timestamp, operation type, user, and full before/after data — giving you a complete reconstruction history even if the database is lost.

### Automatic Backups

On every startup, the app creates a timestamped backup of both the database and the audit log. Backups are stored in `backend/data/backups/` by default and rotated to keep the 10 most recent. For cloud redundancy, set `BACKUP_PATH` in `backend/.env` to a OneDrive (or any synced) folder:

```env
BACKUP_PATH=C:/Users/yourname/OneDrive/TallyUs-Backups
```

Backups use the SQLite online backup API — consistent snapshots safe to create while the app is running.

### SQLite Hardening

The database runs in WAL (Write-Ahead Logging) mode for crash recovery, and an integrity check runs on every startup to detect corruption early. Indexes on `date`, `category`, and `paid_by` are created automatically on startup for faster queries.

### Security

- **Passwords** are stored as bcrypt hashes in `backend/.env` — plaintext passwords are never stored
- **Session cookies** are HMAC-SHA256 signed with a required `SECRET_KEY` — the app refuses to start without one
- **Avatar uploads** are validated with magic byte checks and path traversal protection
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
cd TallyUs
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
# BACKUP_PATH=C:/Users/yourname/OneDrive/TallyUs-Backups
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
| `GET` | `/analytics` | Aggregated analytics (query: `start_date`, `end_date`) |
| `GET` | `/export` | Download filtered expenses as `.xlsx` (query: `search`, `paid_by`, `category`) |

## Project Structure

```
backend/
  config.example.py      # Template — copy to config.py and edit with your names
  config.py              # Your local config (gitignored)
  .env                   # Passwords & session secret (not committed — see .env.example)
  main.py                # FastAPI app & CORS config
  database.py            # SQLite engine (WAL mode), session provider, integrity check
  models.py              # Expense table & Pydantic schemas
  migrate_xlsx.py        # Bulk import from .xlsx
  requirements.txt       # Python dependencies
  services/
    audit.py             # Append-only JSONL audit logger
    backup.py            # Startup backup manager (SQLite online backup API)
  routes/
    expenses.py          # CRUD, balance, monthly summary, description similarity & merge
    analytics.py         # Date-filtered analytics aggregation
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
    App.jsx              # Route definitions & layout shell (includes /edit/:id)
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
      History.jsx        # Expense table with delete/export, edit navigates to /edit/:id
```

## License

This project is licensed under the [MIT License](LICENSE).
