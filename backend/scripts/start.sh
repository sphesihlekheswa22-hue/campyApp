#!/usr/bin/env bash
set -euo pipefail

alembic upgrade head

# One-time demo seed without Render Shell:
# Set SEED_DEMO_DATA=true in Render → Manual Deploy → then set it back to false
# (or delete the var) so the next restart does not wipe data again.
if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  echo "[STARTUP] SEED_DEMO_DATA=true — resetting and seeding demo data"
  python -m app.seed --reset
elif [ "${APP_ENV:-development}" = "production" ]; then
  python -m app.seed --owner-only
else
  python -m app.seed
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
