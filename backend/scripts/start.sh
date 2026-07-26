#!/usr/bin/env bash
set -euo pipefail

alembic upgrade head

if [ "${APP_ENV:-development}" = "production" ]; then
  python -m app.seed --owner-only
else
  python -m app.seed
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
