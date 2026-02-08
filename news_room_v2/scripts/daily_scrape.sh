#!/bin/bash
# Daily Scraping Script for Cron Job
# Schedule: 0 7 * * * (Every day at 7:00 AM)

# Get the absolute path of the script directory
# Get the absolute path of the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Create logs directory if it doesn't exist
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# Get today's date for the log file
TODAY=$(date +%Y%m%d)
LOG_FILE="$LOG_DIR/$TODAY.log"

echo "=== Daily Scraping Started at $(date) ===" >> "$LOG_FILE"

# Run the scraper for today
"$REPO_ROOT/venv_newsroom/bin/python3" "$PROJECT_ROOT/scrapers/history_scraper.py" --date "$TODAY" >> "$LOG_FILE" 2>&1

# Update Vector DB with new data
echo "=== Updating Vector DB ===" >> "$LOG_FILE"
"$REPO_ROOT/venv_newsroom/bin/python3" "$PROJECT_ROOT/core/vector_store.py" >> "$LOG_FILE" 2>&1

# Run Simulation to generate fresh recommendations
echo "=== Generating Daily Recommendations ===" >> "$LOG_FILE"
"$REPO_ROOT/venv_newsroom/bin/python3" "$PROJECT_ROOT/core/simulate.py" --json_output "$PROJECT_ROOT/data/loop_output.json" >> "$LOG_FILE" 2>&1

echo "=== Daily Scraping Completed at $(date) ===" >> "$LOG_FILE"
