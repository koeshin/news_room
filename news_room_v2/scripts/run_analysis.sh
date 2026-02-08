#!/bin/bash
# Get the absolute path of the script directory
# Get the absolute path of the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

echo "🚀 Running News Room Analysis..."

# 1. Update Vector DB (Ingest new scraped data)
echo "📥 Ingesting Data into Vector DB..."
"$REPO_ROOT/venv_newsroom/bin/python3" "$PROJECT_ROOT/core/vector_store.py"

# 2. Run Simulation
echo "🧠 Running Simulation & Recommendation..."
"$REPO_ROOT/venv_newsroom/bin/python3" "$PROJECT_ROOT/core/simulate.py"
