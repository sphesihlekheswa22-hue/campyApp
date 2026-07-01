#!/usr/bin/env bash
set -euo pipefail

pip install -r requirements-render.txt

cd ../frontend
npm ci
npm run build:css
