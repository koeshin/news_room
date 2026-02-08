#!/bin/bash
# Move to the project directory if needed
# cd "$(dirname "$0")"

echo "Starting News Room v2 Web App (FastAPI)..."
echo "URL: http://localhost:8000"

# Kill existing processes
pkill -f uvicorn

# Run uvicorn
../venv_newsroom/bin/uvicorn web.main:app --host 0.0.0.0 --port 8000 --reload
