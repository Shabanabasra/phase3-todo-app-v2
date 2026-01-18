#!/bin/bash
# Production startup script for the backend

# Exit on any error
set -e

echo "Starting Phase-3 AI Todo Backend..."

# Install dependencies
pip install --no-cache-dir -r requirements.txt

# Run database migrations if using Alembic
# alembic upgrade head

# Start the application with uvicorn
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers ${WORKERS:-4} \
    --timeout-keep-alive 30 \
    --proxy-headers \
    --forwarded-allow-ips "*"