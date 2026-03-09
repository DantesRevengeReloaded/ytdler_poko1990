#!/usr/bin/env bash
# setup_db.sh — Create/fix the pokodler PostgreSQL user and database.
# Run with:  sudo bash setup_db.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

DB_USER="${POKODLER_DB_USER:-pokodler}"
DB_PASS="${POKODLER_DB_PASSWORD:-}"
DB_NAME="${POKODLER_DB_NAME:-pokodler}"
PG_PORT="${POKODLER_DB_PORT:-5432}"
DB_HOST="${POKODLER_DB_HOST:-127.0.0.1}"

if [[ -z "$DB_PASS" ]]; then
  echo "POKODLER_DB_PASSWORD is required. Set it in .env or the environment."
  exit 1
fi

echo "==> ytdler DB setup"
echo "    User:     $DB_USER"
echo "    Database: $DB_NAME"
echo "    Host:     $DB_HOST"
echo "    Port:     $PG_PORT"
echo ""

# ── 1. Create / update the role ────────────────────────────────────────────────
echo "[1/4] Creating role '$DB_USER' (or updating password)..."
sudo -u postgres psql -p "$PG_PORT" -c \
  "DO \$\$ BEGIN
     IF EXISTS (SELECT FROM pg_roles WHERE rolname='$DB_USER') THEN
       ALTER ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASS';
       RAISE NOTICE 'Role exists — password updated.';
     ELSE
       CREATE ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASS';
       RAISE NOTICE 'Role created.';
     END IF;
   END \$\$;"

# ── 2. Create database (createdb handles "already exists" gracefully) ──────────
echo "[2/4] Creating database '$DB_NAME'..."
if sudo -u postgres psql -p "$PG_PORT" -lqt | cut -d\| -f1 | grep -qw "$DB_NAME"; then
  echo "      Database already exists — skipping."
else
  sudo -u postgres createdb -p "$PG_PORT" -O "$DB_USER" "$DB_NAME"
  echo "      Database created."
fi

# ── 3. Test connection ─────────────────────────────────────────────────────────
echo "[3/4] Testing connection as '$DB_USER'..."
PGPASSWORD="$DB_PASS" psql \
  -h "$DB_HOST" -p "$PG_PORT" \
  -U "$DB_USER" -d "$DB_NAME" \
  -c "SELECT 'Connection OK' AS status;"

# ── 4. Run ensure_tables via Python ───────────────────────────────────────────
echo "[4/4] Running ensure_tables (creates downloaded_songs, spotify_downloads, jobs)..."
PYTHONPATH="$SCRIPT_DIR" "$SCRIPT_DIR/venv/bin/python" -c "
from app.db.session import init_pool
from app.db.init_db import ensure_tables
init_pool()
ensure_tables()
print('  Tables OK')
"

echo ""
echo "==> Done. Start the app with:"
echo "    cd $SCRIPT_DIR && venv/bin/uvicorn app.main:app --reload"
