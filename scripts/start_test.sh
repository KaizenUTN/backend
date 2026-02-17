#!/bin/bash
# Script para ejecutar tests

export DJANGO_SETTINGS_MODULE=config.settings.test

echo "Running tests with coverage..."
pytest --ds=config.settings.test --cov=apps --cov-report=html --cov-report=term-missing

echo ""
echo "Coverage report generated in htmlcov/index.html"
