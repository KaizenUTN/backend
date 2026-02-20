#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# test.sh — Ejecuta la suite de tests.
#
# Uso:
#   bash scripts/host/test.sh              # corre localmente (requiere venv)
#   bash scripts/host/test.sh --docker     # corre dentro del contenedor Docker
#   bash scripts/host/test.sh -k test_name # filtra tests por nombre (local)
#
# El entorno de tests usa SQLite en memoria; no necesita DB externa.
# ─────────────────────────────────────────────────────────────────
set -e

COMPOSE_FILE="docker-compose.test.yaml"

if [ "$1" = "--docker" ]; then
  echo "[TEST] Running tests in Docker..."
  docker-compose -f $COMPOSE_FILE up --build --abort-on-container-exit
  EXIT_CODE=$(docker inspect django_test --format='{{.State.ExitCode}}' 2>/dev/null || echo "0")
  docker-compose -f $COMPOSE_FILE down
  echo ""
  [ "$EXIT_CODE" = "0" ] && echo "All tests passed ✓" || echo "Tests failed ✗"
  exit $EXIT_CODE
else
  echo "[TEST] Running tests locally..."
  export DJANGO_SETTINGS_MODULE=config.settings.test
  python -m pytest \
    --ds=config.settings.test \
    --tb=short \
    -q \
    --cov=apps \
    --cov-report=html \
    --cov-report=term-missing \
    "$@"
fi
