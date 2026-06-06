#!/bin/sh
set -eu
cd /app
if [ "${FHD_SKIP_ALEMBIC:-0}" != "1" ] && [ -n "${DATABASE_URL:-}" ]; then
  alembic -c alembic.ini upgrade head || exit 1
fi
if [ "${FHD_SKIP_ADMIN_BOOTSTRAP:-0}" != "1" ]; then
  python -c "from app.db.admin_init import create_admin_from_env; print(create_admin_from_env())" || true
fi
exec "$@"
