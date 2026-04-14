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

# Copy startup script
COPY scripts/start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 8000

CMD ["/start.sh"]
