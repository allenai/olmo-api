#!/bin/bash
set -e

echo "Starting FastAPI with uvicorn..."
exec uvicorn app:app --host 0.0.0.0 --port 8000 --reload