#!/bin/bash

set -u -o pipefail

cd "$(dirname "$0")"

APP_URL="http://localhost:8000"

if [[ ! -x "venv/bin/python3" ]]; then
    echo "Creating virtual environment at ./venv"
    python3 -m venv venv
fi

VENV_PY="./venv/bin/python3"
PY_BIN="$VENV_PY"

pause_on_error() {
    local msg="$1"
    echo "$msg"
    if [[ -t 0 ]]; then
        read -r -p "Press Enter to exit..."
    fi
    exit 1
}

check_missing_deps() {
    local py_bin="$1"
    "$py_bin" - <<'PY'
import importlib.util
import sys

required = ["fastapi", "uvicorn", "yt_dlp", "dotenv"]
missing = [m for m in required if importlib.util.find_spec(m) is None]
if missing:
    print("MISSING:" + ",".join(missing))
    sys.exit(1)
PY
}

if ! check_missing_deps "$VENV_PY" > /tmp/pokodler_depcheck.txt 2>&1; then
    echo "Installing/updating dependencies in ./venv ..."
    "$VENV_PY" -m ensurepip --upgrade >/dev/null 2>&1 || true
    if ! "$VENV_PY" -m pip install -r requirements.txt; then
        cat /tmp/pokodler_depcheck.txt || true
        echo "Dependency install in venv failed."
        echo "Trying system Python as fallback ..."
        if check_missing_deps python3 >/tmp/pokodler_depcheck_system.txt 2>&1; then
            PY_BIN="python3"
            echo "Using system Python environment."
        else
            cat /tmp/pokodler_depcheck_system.txt || true
            pause_on_error "Dependencies are missing in both venv and system Python. Run: ./venv/bin/python3 -m pip install -r requirements.txt"
        fi
    fi
fi

echo "Starting FastAPI server on $APP_URL"
"$PY_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
SERVER_PID=$!

open_url() {
    if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
        echo "No GUI session detected. Open this URL manually: $APP_URL"
        return 1
    fi

    if command -v chromium-browser >/dev/null 2>&1; then
        chromium-browser --app="$APP_URL" --class=PokoDler --new-window >/dev/null 2>&1 &
        return 0
    fi

    if command -v chromium >/dev/null 2>&1; then
        chromium --app="$APP_URL" --class=PokoDler --new-window >/dev/null 2>&1 &
        return 0
    fi

    if command -v google-chrome >/dev/null 2>&1; then
        google-chrome --app="$APP_URL" --class=PokoDler --new-window >/dev/null 2>&1 &
        return 0
    fi

    if command -v brave-browser >/dev/null 2>&1; then
        brave-browser --app="$APP_URL" --class=PokoDler --new-window >/dev/null 2>&1 &
        return 0
    fi

    if command -v microsoft-edge >/dev/null 2>&1; then
        microsoft-edge --app="$APP_URL" --class=PokoDler --new-window >/dev/null 2>&1 &
        return 0
    fi

    if command -v firefox >/dev/null 2>&1; then
        firefox --new-window "$APP_URL" >/dev/null 2>&1 &
        return 0
    fi

    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$APP_URL" >/dev/null 2>&1 &
        return 0
    fi

    return 1
}

if ! open_url; then
    echo "Browser not opened automatically. Please open $APP_URL in your browser."
fi

wait "$SERVER_PID"
