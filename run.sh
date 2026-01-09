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

if command -v xdg-open > /dev/null 2>&1; then
    xdg-open http://localhost:8000 &
else
    echo "Browser not opened automatically. Please open http://localhost:8000 in your browser."
fi
wait