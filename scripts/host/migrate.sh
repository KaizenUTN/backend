#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# migrate.sh — Gestiona migraciones de Django.
#
# Uso:
#   bash scripts/host/migrate.sh                 # aplica migraciones (dev)
#   bash scripts/host/migrate.sh --make          # genera + aplica (dev)
#   bash scripts/host/migrate.sh --make prod     # genera + aplica (prod)
#   bash scripts/host/migrate.sh --show          # muestra estado de migraciones
#
# NOTA: makemigrations genera archivos de código que deben committearse.
#       Nunca se ejecuta automáticamente en el startup del contenedor.
# ─────────────────────────────────────────────────────────────────
set -e

ACTION="${1:---apply}"
ENVIRONMENT="${2:-dev}"

export DJANGO_SETTINGS_MODULE="config.settings.$ENVIRONMENT"

echo "[MIGRATE] Ambiente: $ENVIRONMENT"

case "$ACTION" in
  --make)
    echo "[MIGRATE] Generando migraciones..."
    python manage.py makemigrations
    echo "[MIGRATE] Aplicando migraciones..."
    python manage.py migrate
    echo "[MIGRATE] ¡Listo! Committeá los archivos de migración generados."
    ;;
  --show)
    echo "[MIGRATE] Estado actual de migraciones:"
    python manage.py showmigrations
    ;;
  *)
    echo "[MIGRATE] Aplicando migraciones pendientes..."
    python manage.py migrate
    echo "[MIGRATE] ¡Listo!"
    ;;
esac
