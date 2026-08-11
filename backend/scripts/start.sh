#!/usr/bin/env bash
set -euo pipefail

alembic upgrade head

# Keep startup fast so Render health checks pass.
# Heavy demo seed must NOT block uvicorn (it takes minutes).
if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  echo "[STARTUP] SEED_DEMO_DATA=true — seeding in background (non-blocking)"
  (
    python -m app.seed --reset
    echo "[STARTUP] Background seed finished"
  ) >> /tmp/seed-demo.log 2>&1 &
elif [ "${APP_ENV:-development}" = "production" ]; then
  python -m app.seed --owner-only
else
  python -m app.seed
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
