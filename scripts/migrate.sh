#!/bin/bash
# Script para ejecutar migraciones

# Determinar el ambiente (por defecto: dev)
ENVIRONMENT=${1:-dev}

export DJANGO_SETTINGS_MODULE=config.settings.$ENVIRONMENT

echo "Running migrations for $ENVIRONMENT environment..."
python manage.py migrate

echo "Migrations completed!"
