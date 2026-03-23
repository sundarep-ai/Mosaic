# TallyUs — Setup Instructions

Step-by-step guide to get TallyUs running from scratch on a fresh machine.

---

## 1. Prerequisites

| Tool | Minimum Version | Download |
|---|---|---|
| Python | 3.10+ | https://www.python.org/downloads/ |
| Node.js | 18+ | https://nodejs.org/ |
| Git | any | https://git-scm.com/downloads |

Verify installations:

```bash
python --version
node --version
npm --version
git --version
```

---

## 2. Clone the Repository

```bash
git clone <your-repo-url>
cd ExpenseTracking
```

---

## 3. Backend Setup

### 3a. Create a virtual environment

```bash
cd backend
python -m venv venv
```

### 3b. Activate the virtual environment

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate
```

**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

> If PowerShell blocks the script, run this first:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

**macOS / Linux:**
```bash
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### 3c. Install Python dependencies

```bash
pip install -r requirements.txt
```

This installs: FastAPI, Uvicorn, SQLModel, openpyxl, python-multipart.

### 3d. Database setup (SQLite)

There is **no manual database setup required**. Here's how it works:

- TallyUs uses **SQLite**, a file-based database that requires no separate server or installation — it ships with Python.
- The database file `tallyus.db` is created automatically in the `backend/` directory the first time the backend starts.
- The `Expense` table schema is managed by **SQLModel**. On startup, the app calls `SQLModel.metadata.create_all()` which creates any missing tables.
- To inspect the database manually, you can use any SQLite browser (e.g., [DB Browser for SQLite](https://sqlitebrowser.org/)) and open `backend/tallyus.db`.

You do not need to run any migration commands or create the database yourself — just start the server.

### 3e. Start the backend server

```bash
uvicorn main:app --reload
```

The API is now live at **http://localhost:8000**.

- Swagger UI (interactive docs): http://localhost:8000/docs
- ReDoc (alternative docs): http://localhost:8000/redoc

On startup you should see output like:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

At this point `backend/tallyus.db` exists and the `Expense` table is ready.

---

## 4. Frontend Setup

Open a **second terminal** (keep the backend running in the first).

### 4a. Install Node dependencies

```bash
cd frontend
npm install
```

### 4b. Start the dev server

```bash
npm run dev
```

The app is now live at **http://localhost:5173**.

---

## 5. Verify Everything Works

1. Open http://localhost:5173 in your browser.
2. You should see the TallyUs dashboard (empty state — "All settled up!").
3. Click **Add Expense** and log a test expense.
4. Return to the dashboard and confirm the balance updates, the expense appears in recent activity, and the monthly summary shows the category.
5. Visit **Analytics** — charts will populate once you have a few expenses.
6. Visit **History** — verify the expense appears, try edit and delete.
7. Click **Export .xlsx** — a file should download.

---

## 6. Import Existing Data from .xlsx

If you have an existing spreadsheet of expenses:

```bash
cd backend
python migrate_xlsx.py path/to/your/expenses.xlsx
```

### Expected spreadsheet format

The first row must be headers. Column matching is flexible (case-insensitive, tolerates underscores/hyphens):

| Column Header | Required | Example Values |
|---|---|---|
| Date | Yes | `2026-01-15`, `01/15/2026`, `15/01/2026` |
| Description | Yes | `Weekly groceries`, `Electric bill` |
| Amount | Yes | `45.50`, `1200` |
| Category | Yes | `Groceries`, `Rent`, `Utilities`, `Dining`, `Transportation`, `Entertainment`, `Healthcare`, `Shopping`, `Travel`, `Other` |
| Paid By | Yes | `User A`, `User B` |
| Split Method | Yes | `50/50`, `100% User A`, `100% User B`, `Personal` |

Supported date formats: `YYYY-MM-DD`, `MM/DD/YYYY`, `DD/MM/YYYY`, `MM-DD-YYYY`.

The script prints a count on success:
```
Successfully migrated 42 expenses into tallyus.db
```

If a column can't be detected, it prints an error listing the missing fields and the headers it found.

---

## 7. Stopping the Servers

- **Backend:** Press `Ctrl+C` in the first terminal.
- **Frontend:** Press `Ctrl+C` in the second terminal.
- **Deactivate venv:** Run `deactivate` in the backend terminal.

---

## 8. Starting Again Later

```bash
# Terminal 1 — Backend
cd backend
venv\Scripts\activate          # or: source venv/bin/activate
uvicorn main:app --reload

# Terminal 2 — Frontend
cd frontend
npm run dev
```

No reinstall needed — dependencies persist in `venv/` and `node_modules/`.

---

## 9. Resetting the Database

To start fresh, delete the database file and restart the backend:

```bash
cd backend
del tallyus.db                 # Windows
# rm tallyus.db                # macOS / Linux
uvicorn main:app --reload      # recreates an empty database
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` not found | Try `python3` instead, or add Python to your PATH |
| `npm` not found | Install Node.js from https://nodejs.org/ |
| PowerShell blocks `activate` | Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| Port 8000 already in use | Run `uvicorn main:app --reload --port 8001` and update `API_BASE` in `frontend/src/api/expenses.js` |
| Port 5173 already in use | Vite auto-picks the next available port — check terminal output |
| CORS errors in browser | Make sure the backend is running on `localhost:8000` before opening the frontend |
| Migration script fails | Check that your `.xlsx` has a header row and columns match the expected names (see section 6) |
