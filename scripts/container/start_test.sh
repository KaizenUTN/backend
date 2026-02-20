#!/bin/bash
set -e
# ─────────────────────────────────────────────────────────────────
# start_test.sh — Ejecuta la suite de tests con cobertura.
# Corre DENTRO del contenedor (o localmente con venv activo).
# ─────────────────────────────────────────────────────────────────

export DJANGO_SETTINGS_MODULE=config.settings.test

echo "Running test suite..."
python -m pytest \
  --ds=config.settings.test \
  --tb=short \
  -q \
  --cov=apps \
  --cov-report=html \
  --cov-report=term-missing

echo ""
echo "Coverage report: htmlcov/index.html"
