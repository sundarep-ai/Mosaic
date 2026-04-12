# Contributing to Mosaic

Thank you for your interest in contributing. This document explains how to get the development environment running, how the codebase is organized, and how to submit changes.

---

## Before you start

Check the [open issues](../../issues) to see if what you want to work on already has a discussion or is in progress. If it is a non-trivial change, open an issue first so we can discuss the approach before you invest time writing code. For small fixes (typos, obvious bugs), a pull request is fine without a prior issue.

---

## Development setup

Follow the [README setup steps](README.md) to get the app running locally. There are no separate development-only configuration steps — the same setup used for running the app is used for development.

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # macOS / Linux
pip install -r requirements.txt
uvicorn main:app --reload
```

The `--reload` flag restarts the server automatically on file changes.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite's dev server proxies `/api` requests to the backend at `localhost:8000`, so you do not need to configure CORS or change any URLs.

---

## Project structure

```
backend/
  main.py                # FastAPI app, CORS, startup hooks
  database.py            # SQLite engine (WAL mode), session provider
  models.py              # SQLModel table definitions
  auth.py                # Authentication, registration, password management
  users.py               # Dynamic user resolution
  routes/
    expenses.py          # Expense CRUD, balance, merge
    analytics.py         # Aggregated analytics
    insights.py          # Recurring detection, trends, anomalies, forecast
    income.py            # Income CRUD and summaries
    export.py            # .xlsx export
  services/
    audit.py             # Append-only JSONL audit logger
    backup.py            # Startup backup manager
    clustering.py        # Embedding model and cosine-similarity clustering

frontend/src/
  pages/                 # One file per route (Landing, Analytics, Calendar, etc.)
  components/            # Shared UI components (Navbar, DateInput, modals)
  hooks/                 # Custom React hooks
  api/                   # Fetch helpers per domain (expenses, income)
  constants/             # Categories, income sources, shared mappings
  context/               # Auth, currency, date format, config contexts
```

---

## Making changes

### Backend

- Routes live in `backend/routes/`. Each file maps to a domain (expenses, analytics, income, etc.).
- Database models are in `backend/models.py`. SQLModel manages table creation on startup — there is no migration tooling. If you add a column, add a default value so existing rows are unaffected.
- The audit log (`services/audit.py`) must be called for any mutation (create, update, delete). Do not skip it.
- All monetary values stored in the database are in the user's original currency with no conversion. The currency selector is display-only.

### Frontend

- Each page is a single file in `frontend/src/pages/`.
- Shared UI components live in `frontend/src/components/`.
- API calls should go through the helpers in `frontend/src/api/` using `fetchWithAuth`, which handles 401 responses automatically.
- The date format preference is stored per user in the database and accessed through `DateFormatContext`. Use the `DateInput` component for any date field — do not use native `<input type="date">`.
- Currency symbol rendering should use `CurrencyContext` — do not hardcode symbols.

---

## Code style

There is no enforced linter configuration. Follow the style of the surrounding code:

- **Python** — standard Python conventions, type hints where they add clarity, no unnecessary abstractions.
- **JavaScript / JSX** — functional components, hooks for state, Tailwind for styling. Avoid adding new dependencies unless necessary.

---

## Submitting a pull request

1. Fork the repository and create a branch from `main`.
2. Make your changes. Keep the scope of each pull request focused — one feature or fix per PR.
3. Test your changes manually against the relevant flows (adding expenses, switching modes, edge cases).
4. Open a pull request against `main` with a clear title and description of what changed and why.

There is currently no automated test suite. Manual testing of the affected flows is expected before submitting.

---

## Reporting bugs

Open an issue with:

- What you expected to happen.
- What actually happened.
- Steps to reproduce.
- Your OS, browser, and Python / Node.js versions.

---

## Feature requests

Open an issue describing the feature and the problem it solves. Features that serve the core use case (personal and shared expense tracking, offline/local-first) are more likely to be accepted than features that add complexity without broad benefit.
