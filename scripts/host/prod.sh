#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# prod.sh — Levanta el entorno de producción desde cero.
#
# Uso:
#   bash scripts/host/prod.sh              # build + start (background)
#   bash scripts/host/prod.sh --down       # detiene y elimina contenedores
#   bash scripts/host/prod.sh --logs       # muestra logs en tiempo real
#
# El contenedor ejecuta automáticamente:
#   migrate → seed_authorization → collectstatic → gunicorn
#
# IMPORTANTE: asegurarse de tener .env.prod configurado antes de correr.
# ─────────────────────────────────────────────────────────────────
set -e

COMPOSE_FILE="docker-compose.prod.yaml"

if [ ! -f ".env.prod" ]; then
  echo "ERROR: .env.prod not found. Copy .env.example and configure it first."
  exit 1
fi

case "$1" in
  --down)
    echo "Stopping production environment..."
    docker-compose -f $COMPOSE_FILE down
    ;;
  --logs)
    docker-compose -f $COMPOSE_FILE logs -f
    ;;
  *)
    echo "Building and starting production environment..."
    docker-compose -f $COMPOSE_FILE up --build -d
    echo ""
    echo "Production environment started ✓"
    echo ""
    echo "Useful commands:"
    echo "  Logs:   bash scripts/host/prod.sh --logs"
    echo "  Stop:   bash scripts/host/prod.sh --down"
    echo "  Shell:  docker-compose -f $COMPOSE_FILE exec web bash"
    ;;
esac
