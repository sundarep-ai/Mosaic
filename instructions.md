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
cd TallyUs
```

---

## 3. Configure Users

All personalization lives in two backend files. The frontend fetches user names from the backend automatically — no frontend config needed.

### 3a. Set display names and login usernames

Copy the example config file, then edit it with your own names:

```bash
cd backend
cp config.example.py config.py
```

Edit **`backend/config.py`**:

```python
USER_A = "Alice"          # Display name for user A
USER_B = "Bob"            # Display name for user B

USER_A_LOGIN = "alice"    # Login username for user A
USER_B_LOGIN = "bob"      # Login username for user B
```

> **Note:** `config.py` is gitignored — it contains your personal settings. Always start from `config.example.py`.

### 3b. Set passwords and session secret

Copy the example env file and edit it:

```bash
cd backend
cp .env.example .env
```

Then edit **`backend/.env`**. Passwords must be **bcrypt hashes** (not plaintext) and a **SECRET_KEY** is required:

```env
USER_A_PASSWORD=<bcrypt hash>
USER_B_PASSWORD=<bcrypt hash>
SECRET_KEY=<long random string>

# Optional: set to a OneDrive/cloud folder for cloud-synced backups
# BACKUP_PATH=C:/Users/yourname/OneDrive/TallyUs-Backups
```

> **Important:** Never commit `.env` — it's already in `.gitignore`.

#### Generating bcrypt password hashes

> **Note:** This step requires Python dependencies to be installed first (step 4c). You can set placeholder values in `.env` now and come back to generate the real hashes after running `pip install -r requirements.txt`.

Generate hashes for each user's password:

```bash
cd backend
python -c "from auth import hash_password; print(hash_password('your-password-here'))"
```

Copy the output (starts with `$2b$12$...`) into `.env` as the password value.

#### Generating a SECRET_KEY

The `SECRET_KEY` is used to sign session cookies. The app **will not start** without one. Generate a strong random key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the output into `.env` as the `SECRET_KEY` value.

**To enable OneDrive backups**, uncomment `BACKUP_PATH` and set it to any folder that is synced to the cloud (OneDrive, Google Drive, Dropbox, etc.). On each startup, TallyUs will copy both the database and the audit log there.

---

## 4. Backend Setup

### 4a. Create a virtual environment

```bash
cd backend
python -m venv venv
```

### 4b. Activate the virtual environment

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

### 4c. Install Python dependencies

```bash
pip install -r requirements.txt
```

This installs: FastAPI, Uvicorn, SQLModel, openpyxl, python-multipart, fastembed (ONNX-based embeddings for description similarity), and bcrypt (password hashing).

### 4d. Database setup (SQLite)

There is **no manual database setup required**. Here's how it works:

- TallyUs uses **SQLite**, a file-based database that requires no separate server or installation — it ships with Python.
- The database file `tallyus.db` is created automatically in the `backend/` directory the first time the backend starts.
- The `Expense` table schema is managed by **SQLModel**. On startup, the app calls `SQLModel.metadata.create_all()` which creates any missing tables.
- The database runs in **WAL mode** (Write-Ahead Logging) for crash recovery and safe concurrent access.
- **Indexes** on `date`, `category`, and `paid_by` are created automatically on startup for faster queries.
- To inspect the database manually, you can use any SQLite browser (e.g., [DB Browser for SQLite](https://sqlitebrowser.org/)) and open `backend/tallyus.db`.

You do not need to run any migration commands or create the database yourself — just start the server.

### 4e. Start the backend server

```bash
uvicorn main:app --reload
```

The API is now live at **http://localhost:8000**.

- Swagger UI (interactive docs): http://localhost:8000/docs
- ReDoc (alternative docs): http://localhost:8000/redoc

On startup you should see output like:
```
INFO:     Database integrity check passed
INFO:     Backup created at backend/data/backups/2026-03-29T143000
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

At this point `backend/tallyus.db` exists, the `Expense` table is ready, database indexes have been created, and a backup snapshot has been created in `backend/data/backups/` (or your configured `BACKUP_PATH`).

> **Note:** If you see `RuntimeError: SECRET_KEY environment variable is not set`, make sure you've created `backend/.env` with a valid `SECRET_KEY` (see step 3b).

> **Note:** The first time you use the "Clean Up Descriptions" feature (similarity analysis), `fastembed` will download a small embedding model (~45 MB). This is a one-time download that gets cached locally.

---

## 5. Frontend Setup

Open a **second terminal** (keep the backend running in the first).

### 5a. Install Node dependencies

```bash
cd frontend
npm install
```

### 5b. Start the dev server

```bash
npm run dev
```

The app is now live at **http://localhost:5173**.

---

## 6. Verify Everything Works

1. Open http://localhost:5173 in your browser.
2. Log in with one of the usernames and passwords you configured in step 3.
3. You should see the TallyUs dashboard (empty state — "All settled up!").
4. Click **Add Expense** and log a test expense. As you type a description, you should see:
   - A **"Did you mean?"** dropdown suggesting similar existing descriptions (fuzzy matching).
   - The **category auto-filling** instantly based on the closest historical match.
5. Return to the dashboard and confirm the balance updates, the expense appears in recent activity, and the monthly summary shows the category.
6. Visit **Analytics** — charts will populate once you have a few expenses.
7. Visit **History** — verify the expense appears, try edit and delete.
8. Click **Clean Up** on the History page to test the description merge tool. It uses AI embeddings to find groups of similar descriptions (e.g. "Foodbasics" / "Food Basics") and lets you merge them into a canonical form.
9. Click **Export .xlsx** — a file should download.

---

## 7. Import Existing Data from .xlsx

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
| Paid By | Yes | Must match `USER_A` / `USER_B` in `config.py` |
| Split Method | Yes | `50/50`, `100% <User A name>`, `100% <User B name>`, `Personal` |

Supported date formats: `YYYY-MM-DD`, `MM/DD/YYYY`, `DD/MM/YYYY`, `MM-DD-YYYY`.

The script prints a count on success:
```
Successfully migrated 42 expenses into tallyus.db
```

If a column can't be detected, it prints an error listing the missing fields and the headers it found.

---

## 8. Stopping the Servers

- **Backend:** Press `Ctrl+C` in the first terminal.
- **Frontend:** Press `Ctrl+C` in the second terminal.
- **Deactivate venv:** Run `deactivate` in the backend terminal.

---

## 9. Starting Again Later

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

## 10. Resetting the Database

To start fresh, delete the database file and restart the backend:

```bash
cd backend
del tallyus.db                 # Windows
# rm tallyus.db                # macOS / Linux
uvicorn main:app --reload      # recreates an empty database
```

> **Note:** Deleting `tallyus.db` does not delete the audit log or backups in `backend/data/`. Those are preserved independently. If you want a full reset, also delete `backend/data/`.

## 11. Restoring from a Backup

Backups are stored in timestamped subdirectories (e.g., `backend/data/backups/2026-03-29T143000/`), each containing a `tallyus.db` snapshot and an `audit.jsonl` snapshot.

To restore:

```bash
# Stop the backend first (Ctrl+C)
cd backend

# Replace the database with a backup
copy data\backups\2026-03-29T143000\tallyus.db tallyus.db   # Windows
# cp data/backups/2026-03-29T143000/tallyus.db tallyus.db   # macOS / Linux

# Restart the backend
uvicorn main:app --reload
```

The audit log at `backend/data/audit/audit.jsonl` is a permanent append-only record of every change ever made and can be used to reconstruct the state of the database at any point in time.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `RuntimeError: SECRET_KEY environment variable is not set` | Create `backend/.env` with a `SECRET_KEY` value (see step 3b) |
| Login fails after upgrading to bcrypt | Passwords in `.env` must be bcrypt hashes, not plaintext. Regenerate them (see step 3b) |
| `python` not found | Try `python3` instead, or add Python to your PATH |
| `npm` not found | Install Node.js from https://nodejs.org/ |
| PowerShell blocks `activate` | Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| Port 8000 already in use | Run `uvicorn main:app --reload --port 8001` and update `VITE_API_BASE` in `frontend/.env` |
| Port 5173 already in use | Vite auto-picks the next available port — check terminal output |
| CORS errors in browser | Make sure the backend is running on `localhost:8000` before opening the frontend |
| Migration script fails | Check that your `.xlsx` has a header row and columns match the expected names (see section 6) |
| Backup directory not created | The `backend/data/` folder is created automatically on first startup — no manual action needed |
| `BACKUP_PATH` not working | Make sure the path exists and uses forward slashes or escaped backslashes in `.env` |
| `.db-shm` / `.db-wal` files appeared | Normal — these are SQLite WAL mode working files, managed automatically. They are gitignored. |
