#!/bin/bash
set -e

echo "========================================"
echo "  Dev Environment — Startup"
echo "========================================"

export DJANGO_SETTINGS_MODULE=config.settings.dev

# ── 1. Esperar a PostgreSQL ────────────────────────────────────────────────
echo "[1/5] Waiting for database..."
until pg_isready -h "${POSTGRES_HOST:-db}" -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-postgres}" -q; do
  echo "  Postgres not ready — retrying in 2s..."
  sleep 2
done
echo "  Database ready ✓"

# ── 2. Migraciones ─────────────────────────────────────────────────────────
echo "[2/5] Running migrations..."
python manage.py migrate --noinput

# ── 3. Seed RBAC ──────────────────────────────────────────────────────────
echo "[3/5] Seeding authorization roles & permissions..."
python manage.py seed_authorization

# ── 4. Superusuario de desarrollo ─────────────────────────────────────────
echo "[4/5] Creating dev superuser (admin@gmail.com)..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
email = 'admin@gmail.com'
if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email=email, password='1234')
    print('  Superuser created ✓')
else:
    print('  Superuser already exists — skipped.')
"

# ── 5. Servidor de desarrollo ─────────────────────────────────────────────
echo "[5/5] Starting development server at 0.0.0.0:8000"
echo "========================================"
exec python manage.py runserver 0.0.0.0:8000