# Single image: builds the React frontend, then runs the FastAPI backend which
# serves both the API and the built frontend on one port (see FRONTEND_DIST in
# backend/main.py). No nginx / reverse proxy needed — one image, one container.

# Stage 1: build the React frontend
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: backend + the built frontend it serves
FROM python:3.13-slim
WORKDIR /app/backend

# Install dependencies first (cached layer — only re-runs if requirements.txt changes)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download fastembed ONNX model during build so the container starts instantly
# without requiring internet access or download time at runtime
RUN python -c "from fastembed import TextEmbedding; TextEmbedding()"

# Copy backend source
COPY backend/ .

# config.py is gitignored (no secrets — just reads env vars).
# On a fresh clone it won't exist, so fall back to config.example.py.
RUN test -f config.py || cp config.example.py config.py

# Built SPA from stage 1 — FastAPI serves it from ../frontend/dist
COPY --from=frontend /app/frontend/dist /app/frontend/dist

# Copy startup script (creates data dirs, then launches uvicorn on :8000)
COPY scripts/start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 8000

CMD ["/start.sh"]
