#!/bin/bash

# Script to run the PokoDler FastAPI application

# Navigate to the project directory (adjust if needed)
cd "$(dirname "$0")"

# Activate virtual environment if it exists (optional, uncomment if you have a venv)
source venv/bin/activate  # or wherever your venv is

# Install dependencies if not already installed (optional)
# pip install -r requirements.txt

# Run the FastAPI app with uvicorn
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

# Try to open the UI in a minimal app-like window instead of the default browser
APP_URL="http://localhost:8000"
if command -v chromium-browser > /dev/null 2>&1; then
    chromium-browser --app="$APP_URL" --class=PokoDler --new-window &
elif command -v chromium > /dev/null 2>&1; then
    chromium --app="$APP_URL" --class=PokoDler --new-window &
elif command -v google-chrome > /dev/null 2>&1; then
    google-chrome --app="$APP_URL" --class=PokoDler --new-window &
elif command -v brave-browser > /dev/null 2>&1; then
    brave-browser --app="$APP_URL" --class=PokoDler --new-window &
elif command -v microsoft-edge > /dev/null 2>&1; then
    microsoft-edge --app="$APP_URL" --class=PokoDler --new-window &
elif command -v firefox > /dev/null 2>&1; then
    firefox --new-window "$APP_URL" &
elif command -v xdg-open > /dev/null 2>&1; then
    xdg-open "$APP_URL" &
else
    echo "Browser not opened automatically. Please open $APP_URL in your browser."
fi
wait