<p align="center">
  <img src="assets/logo.png" alt="Mosaic Logo" width="120" height="120" />
</p>

<h1 align="center" style="margin-bottom: 0; border-bottom: none;">Mosaic</h1>
<p align="center"><i>Local First Expense Tracker</i></p>

<br>

<p align="center">
  <img src="https://img.shields.io/github/actions/workflow/status/sundarep-ai/Mosaic/tests.yml?branch=main&label=Release" alt="Build" />
  &nbsp;
  <img src="https://img.shields.io/github/v/release/sundarep-ai/Mosaic?label=release" alt="Release" />
  &nbsp;
  <img src="https://img.shields.io/docker/pulls/srpraveen97/mosaic?label=docker+pulls" alt="Docker Pulls" />
  &nbsp;
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License" />
</p>

<p align="center">
  <a href="#why-mosaic">Why Mosaic</a>&nbsp;&bull;&nbsp;<a href="#features-at-a-glance">Features</a>&nbsp;&bull;&nbsp;<a href="#setup">Setup</a>&nbsp;&bull;&nbsp;<a href="#method-3-docker">Docker</a>&nbsp;&bull;&nbsp;<a href="FEATURES.md">Full Docs</a>&nbsp;&bull;&nbsp;<a href="CONTRIBUTING.md">Contributing</a>
</p>

---

Mosaic is a personal expense tracker that runs entirely on your own machine. No subscriptions, no data sent anywhere. Log expenses, understand your spending patterns, and get automated analysis all locally. Mosaic also scales to two: a Blended mode lets couples track personal and shared expenses side by side without mixing them up.

---

## Why Mosaic

**Insights that actually tell you something.**
Mosaic analyses your spending automatically: it detects recurring expenses, flags anomalies, alerts you when a category spikes above its 3-month average, and forecasts next month's spending. No manual setup, it works from the data you've already logged.

**AI-powered description clean-up, on your device.**
Tracked the same grocery store as "Foodbasics", "Food Basics", and "food basics"? The Clean Up tool uses local ONNX embeddings to find description variants that refer to the same thing and lets you merge them in bulk. No API calls, no data leaving your machine.

**A calendar that shows where your money goes.**
A monthly heat-map calendar colours each day by spending intensity, making it easy to spot heavy spending days at a glance. Click any day to see exactly what you bought.

**Runs locally, your data stays yours.**
Everything lives in a local database on your machine. Mosaic never leaves home. No third-party access, no cloud sync unless you explicitly configure it (for OneDrive backups).

**Scales to two when you need it.**
Couples can log personal and shared expenses side by side. Mosaic tracks who owes what, splits costs fairly, and keeps each person's private spending to themselves.

---

## Features at a glance

| | |
|---|---|
| **Dashboard** | Monthly balance, your expense share, income summary, spend by category, recent activity |
| **Add Expense** | Fuzzy description matching, category auto-suggest, custom categories, flexible split methods |
| **Analytics** | Date-range charts, Sankey income-flow diagram, category drill-down, largest outlays |
| **Calendar** | Heat-map month view, income badges, click-to-filter drill-down |
| **Insights** | Anomaly detection, recurring expense tracker, category trend alerts, spend forecast, weekend vs. weekday analysis |
| **History** | Searchable and filterable expense table, edit, delete, spreadsheet export |
| **Clean Up** | AI embedding-based description deduplication with bulk merge |
| **Modes** | Personal (solo), Shared (split everything), Blended (mix of both) |

Full feature documentation: [FEATURES.md](FEATURES.md)

---

## Tech stack

| Layer | Technologies |
|---|---|
| Backend | Python 3.10+, FastAPI, SQLModel, SQLite (WAL mode), fastembed (ONNX embeddings), bcrypt, openpyxl |
| Frontend | React 18 (Vite), Tailwind CSS 3, React Router 6, Recharts, Fuse.js |

---

## Setup

Choose the method that fits your situation:

| Method | Best for | Requirements |
|---|---|---|
| [Development](#method-1-development) | Local dev, experimenting | Python 3.10+, Node.js 18+ |
| [Git clone (production)](#method-2-git-clone-production) | Self-hosting on a machine you control | Python 3.10+, Node.js 18+ |
| [Docker](#method-3-docker) | Cleanest self-hosting, no Python/Node needed on host | Docker Desktop |

The database (`mosaic.db`) is created automatically on first start — no manual setup required. Create up to 2 user accounts through the web UI after launching.

---

### Method 1: Development

Run the backend and frontend as separate dev servers. The frontend proxies API calls to the backend automatically.

**Prerequisites:** Python 3.10+, Node.js 18+

```bash
git clone https://github.com/sundarep-ai/Mosaic.git
cd Mosaic
```

**Backend:**

```bash
cd backend
cp config.example.py config.py
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

Create `backend/.env`:

```env
SECRET_KEY=<long random string>
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(48))"

# Optional: path to a cloud-synced folder for off-site backups
# BACKUP_PATH=C:/Users/yourname/OneDrive/Mosaic-Backups
```

```bash
uvicorn main:app --reload
```

**Frontend** (new terminal):

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**.

> **First run:** The first time you use the Description Clean Up feature, `fastembed` downloads an embedding model (~45 MB). One-time, cached locally.

---

### Method 2: Git clone (production)

FastAPI serves both the API and the built frontend from a single process. No Docker, no reverse proxy.

**Prerequisites:** Python 3.10+, Node.js 18+

```bash
git clone https://github.com/sundarep-ai/Mosaic.git
cd Mosaic
```

**Backend setup:**

```bash
cd backend
cp config.example.py config.py
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

Create `backend/.env`:

```env
SECRET_KEY=<long random string>
ENV=production
COOKIE_SECURE=false

# Optional: cloud backup path
# BACKUP_PATH=C:/Users/yourname/OneDrive/Mosaic-Backups
```

**Build the frontend:**

```bash
cd ../frontend
npm install
npm run build
```

**Run:**

```bash
cd ../backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** (or `http://<your-machine-ip>:8000` from other devices on your network).

**To update to a new version:**

```bash
git pull origin main
cd frontend && npm install && npm run build
cd ../backend && uvicorn main:app --host 0.0.0.0 --port 8000
```

---

### Method 3: Docker

Two containers — nginx serves the frontend and proxies the API, the backend runs uvicorn. All data persists in a Docker named volume across restarts and rebuilds.

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/)

```bash
git clone https://github.com/sundarep-ai/Mosaic.git
cd Mosaic
```

Create a `.env` file (Docker Compose reads this automatically):

```bash
cp .env.docker.example .env
```

Edit `.env` and set your secret key:

```env
SECRET_KEY=<long random string>
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(48))"

# Optional: change the port (default is 80)
# MOSAIC_PORT=8080

# Optional: set to true if serving over HTTPS
# COOKIE_SECURE=true
```

**Build and start:**

```bash
docker compose up -d --build
```

Open **http://localhost** (or `http://localhost:8080` if you changed the port).

> **Build note:** The first build downloads the fastembed ONNX model (~45 MB) and bakes it into the image. Subsequent builds and container restarts use the cached layer — no re-download.

**To update to a new version:**

```bash
git pull origin main
docker compose up -d --build
```

Your data (database, audit logs, backups, avatars) is stored in the `mosaic-data` Docker volume and is never touched by a rebuild.

**To stop:**

```bash
docker compose down
```

---

### Optional: Import existing data

If you have expenses in a `.xlsx` or `.csv` file (works with all methods — run from the backend directory with the venv active, or `docker exec` into the backend container):

```bash
cd backend
python migrate_expenses.py path/to/expenses.xlsx
```

Expected columns: `Date`, `Description`, `Amount`, `Category`, `Paid By`, `Split Method`.

For income history (Personal / Blended mode only):

```bash
python migrate_income.py path/to/income.xlsx
```

Expected columns: `Date`, `Amount`, `Source`, `Display Name`, `Notes` (optional).

### Optional: CLI password reset

If a user cannot answer their security question:

```bash
cd backend
python cli_reset_password.py
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `SECRET_KEY environment variable is not set` | Create `backend/.env` with a `SECRET_KEY` value |
| `python` not found | Try `python3`, or add Python to your PATH |
| `npm` not found | Install Node.js from https://nodejs.org/ |
| PowerShell blocks `activate` | Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| Port 8000 already in use | Run `uvicorn main:app --host 0.0.0.0 --port 8001` |
| Port 5173 already in use | Vite auto-picks the next available port — check the terminal output |
| CORS errors in the browser | Make sure the backend is running on `localhost:8000` before opening the frontend (dev only) |
| `.db-shm` / `.db-wal` files appeared | Normal — SQLite WAL mode working files, managed automatically |
| Docker: `failed to connect to docker API` | Open Docker Desktop and wait for it to fully start |

---

## Links

- [Features](FEATURES.md) — full feature reference
- [Contributing](CONTRIBUTING.md) — how to contribute
- [License](LICENSE) — MIT
