#!/bin/bash
set -e

echo "========================================"
echo "  Dev Environment — Startup"
echo "========================================"

export DJANGO_SETTINGS_MODULE=config.settings.dev

# ── 1. Esperar a PostgreSQL ────────────────────────────────────────────────
echo "[1/4] Waiting for database..."
until pg_isready -h "${POSTGRES_HOST:-db}" -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-postgres}" -q; do
  echo "  Postgres not ready — retrying in 2s..."
  sleep 2
done
echo "  Database ready ✓"

# ── 2. Migraciones ─────────────────────────────────────────────────────────
echo "[2/4] Running migrations..."
python manage.py migrate --noinput

# ── 3. Seed RBAC ──────────────────────────────────────────────────────────
echo "[3/4] Seeding authorization roles & permissions..."
python manage.py seed_authorization

# ── 4. Servidor de desarrollo ─────────────────────────────────────────────
echo "[4/4] Starting development server at 0.0.0.0:8000"
echo "========================================"
exec python manage.py runserver 0.0.0.0:8000