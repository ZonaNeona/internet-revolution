#!/usr/bin/env bash
set -euo pipefail
set -a
. "${PRODUCT_HUNTER_ENV_FILE:-/etc/product-hunter.env}"
set +a
for migration in backend/migrations/*.sql; do
  echo "Applying $migration"
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$migration"
done