<div align="center">

# TallyUs

**A simple, local-first expense tracker for two people.**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Tailwind](https://img.shields.io/badge/Tailwind_CSS-3.4-06B6D4?logo=tailwindcss&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Version](https://img.shields.io/badge/version-0.1.0-blue)

</div>

---

TallyUs tracks shared expenses between two users (User A & User B), calculates who owes whom, and provides visual analytics — all running locally with zero cloud dependencies.

## Features

| Page | What it does |
|---|---|
| **Dashboard** | Live balance ("User A owes User B $50"), this month's spend by category, last 10 expenses |
| **Add Expense** | Log an expense with date, description, category, amount, payer, and split method |
| **Analytics** | Date-range filtered Bar / Pie / Line charts, summary cards, top 5 largest expenses |
| **History** | Full expense table with search, category & payer filters, inline edit, delete with confirmation |
| **Export** | Download the current filtered view as an `.xlsx` file |

### Split Methods

| Method | Behaviour |
|---|---|
| `50/50` | Cost is shared equally — the non-payer owes half |
| `100% User A` | User A is fully responsible regardless of who paid |
| `100% User B` | User B is fully responsible regardless of who paid |
| `Personal` | No balance impact — a personal expense logged for tracking only |

## Tech Stack

| Layer | Technologies |
|---|---|
| Backend | Python 3.10+, FastAPI, SQLModel, SQLite, openpyxl |
| Frontend | React 18 (Vite), Tailwind CSS 3, React Router 6, Recharts, Lucide React |

## Prerequisites

- **Python 3.10+** &nbsp;—&nbsp; [python.org/downloads](https://www.python.org/downloads/)
- **Node.js 18+** &nbsp;—&nbsp; [nodejs.org](https://nodejs.org/)

## Getting Started

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd ExpenseTracking
```

### 2. Start the backend

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

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

### 4. (Optional) Import existing data

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
| Paid By | User A, User B |
| Split Method | 50/50, 100% User A, 100% User B, Personal |

## API Reference

All endpoints are prefixed with `/api`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/expenses` | List expenses (query: `search`, `paid_by`, `category`, `limit`, `sort`) |
| `POST` | `/expenses` | Create a new expense |
| `GET` | `/expenses/{id}` | Get a single expense |
| `PUT` | `/expenses/{id}` | Update an expense |
| `DELETE` | `/expenses/{id}` | Delete an expense |
| `GET` | `/balance` | Current balance between User A & User B |
| `GET` | `/monthly-summary` | Category totals for the current month |
| `GET` | `/analytics` | Aggregated analytics (query: `start_date`, `end_date`) |
| `GET` | `/export` | Download filtered expenses as `.xlsx` (query: `search`, `paid_by`, `category`) |

## Project Structure

```
backend/
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
  vite.config.js         # Vite configuration
  tailwind.config.js     # Tailwind content paths
  index.html             # HTML entry point
  src/
    main.jsx             # React root & router setup
    App.jsx              # Route definitions & layout shell
    index.css            # Tailwind directives
    api/
      expenses.js        # Fetch helpers for all endpoints
    components/
      Navbar.jsx         # Sticky navigation bar
    pages/
      Landing.jsx        # Dashboard page
      AddExpense.jsx     # New expense form
      Analytics.jsx      # Charts & analytics dashboard
      History.jsx        # Expense table with edit/delete/export
```

## License

This project is licensed under the [MIT License](LICENSE).
