#!/bin/bash
set -euo pipefail

# Applies pending Alembic migrations before the app starts — matters for
# Postgres deployments where the schema isn't auto-created the way the
# SQLite dev convenience path does it (see app/main.py's lifespan).
if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
    echo "Running database migrations..."
    alembic upgrade head
fi

exec "$@"
