#!/bin/bash
# Script para iniciar producción

export DJANGO_SETTINGS_MODULE=config.settings.prod

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 60 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --log-level info
