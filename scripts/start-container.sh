#!/bin/sh
set -eu

python -m alembic -c backend/alembic.ini upgrade head
exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
