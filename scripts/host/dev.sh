#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# dev.sh — Levanta el entorno de desarrollo completo desde cero.
#
# Uso:
#   bash scripts/host/dev.sh           # build + start (foreground con logs)
#   bash scripts/host/dev.sh -d        # build + start en background
#   bash scripts/host/dev.sh --down    # detiene y elimina contenedores
#
# El contenedor ejecuta automáticamente:
#   migrate → seed_authorization → runserver
# ─────────────────────────────────────────────────────────────────
set -e

COMPOSE_FILE="docker-compose.dev.yaml"

case "$1" in
  --down)
    echo "Stopping dev environment..."
    docker-compose -f $COMPOSE_FILE down
    ;;
  -d)
    echo "Starting dev environment in background..."
    docker-compose -f $COMPOSE_FILE up --build -d
    echo ""
    echo "Services running. Useful commands:"
    echo "  Logs:    docker-compose -f $COMPOSE_FILE logs -f"
    echo "  Stop:    bash scripts/host/dev.sh --down"
    echo "  Shell:   docker-compose -f $COMPOSE_FILE exec web bash"
    ;;
  *)
    echo "Starting dev environment (foreground)..."
    docker-compose -f $COMPOSE_FILE up --build
    ;;
esac
