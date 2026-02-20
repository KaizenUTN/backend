#!/bin/bash
set -e

echo "========================================"
echo "  Production Environment — Startup"
echo "========================================"

export DJANGO_SETTINGS_MODULE=config.settings.prod

# ── 1. Esperar a PostgreSQL ────────────────────────────────────────────
echo "[1/5] Waiting for database..."
until pg_isready -h "${POSTGRES_HOST:-db}" -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-postgres}" -q; do
  echo "  Postgres not ready — retrying in 2s..."
  sleep 2
done
echo "  Database ready ✓"

# ── 2. Migraciones ─────────────────────────────────────────────────────────
echo "[2/5] Running migrations..."
python manage.py migrate --noinput

# ── 3. Seed RBAC (idempotente) ────────────────────────────────────────────────
echo "[3/5] Seeding authorization roles & permissions..."
python manage.py seed_authorization

# ── 4. Archivos estáticos ─────────────────────────────────────────────────────
echo "[4/5] Collecting static files..."
python manage.py collectstatic --noinput

# ── 5. Gunicorn ────────────────────────────────────────────────────────────
echo "[5/5] Starting Gunicorn..."
echo "========================================"
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 3 \
  --timeout 60 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  --log-level info
