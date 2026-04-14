#!/bin/sh
set -e

# Ensure persistent data directories exist on first run
mkdir -p "${DATA_DIR}/audit"
mkdir -p "${DATA_DIR}/backups"
mkdir -p "${DATA_DIR}/uploads/avatars"

exec uvicorn main:app --host 0.0.0.0 --port 8000
