<div align="center">

# TallyUs

**A simple, local-first expense tracker for two people.**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-3.4-06B6D4?logo=tailwindcss&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Version](https://img.shields.io/badge/version-1.0.0-blue)

</div>

---

TallyUs tracks shared expenses between two people, calculates who owes whom, and provides visual analytics — all running locally with zero cloud dependencies. User names are configured in a single place and flow through both the backend and frontend automatically.

## Features

| Page | What it does |
|---|---|
| **Dashboard** | Live balance (e.g. "User A owes User B $50"), this month's spend by category, last 10 expenses |
| **Add Expense** | Log an expense with date, description, category, amount, payer, and split method. Supports custom categories via "+ New Category" and auto-suggests categories from history. |
| **Edit Expense** | Full-page edit form at `/edit/:id` — reuses the Add Expense form with all fields pre-filled |
| **Analytics** | Date-range filtered Bar / Pie / Line charts, summary cards, top 5 largest expenses |
| **History** | Full expense table with search, category & payer filters, edit (navigates to edit page), delete with confirmation |
| **Export** | Download the current filtered view as an `.xlsx` file |

### Split Methods

| Method | Behaviour |
|---|---|
| `50/50` | Cost is shared equally — the non-payer owes half |
| `100% (Other Owes)` | The non-payer is fully responsible for the expense |
| `Personal` | No balance impact — a personal expense logged for tracking only |

### Validation

- **Amount** must be greater than zero (enforced on both frontend and backend)
- **Date** cannot be in the future (enforced on both frontend and backend)
- **Paid By** and **Split Method** must match the configured user names
- **Category** is free-form — choose from the default list or create a custom category

## Tech Stack

| Layer | Technologies |
|---|---|
| Backend | Python 3.10+, FastAPI, SQLModel, SQLite, openpyxl |
| Frontend | React 18 (Vite), Tailwind CSS 3, React Router 6, Recharts |

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
USER_A_PASSWORD=your-password-here
USER_B_PASSWORD=your-password-here
SECRET_KEY=some-random-secret-key
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
  database.py            # SQLite engine & session provider
  models.py              # Expense table & Pydantic schemas
  migrate_xlsx.py        # Bulk import from .xlsx
  requirements.txt       # Python dependencies
  routes/
    expenses.py          # CRUD, balance, monthly summary
    analytics.py         # Date-filtered analytics aggregation
    export.py            # .xlsx file generation & download

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
      expenses.js        # Fetch helpers for all endpoints
    constants/
      categories.js      # Shared category list, icons, and color mappings
    components/
      Navbar.jsx         # Sticky navigation bar
    pages/
      Landing.jsx        # Dashboard page
      AddExpense.jsx     # New/edit expense form (also handles /edit/:id)
      Analytics.jsx      # Charts & analytics dashboard
      History.jsx        # Expense table with delete/export, edit navigates to /edit/:id
```

## License

This project is licensed under the [MIT License](LICENSE).
