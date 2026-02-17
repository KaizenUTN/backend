#!/bin/bash
export DJANGO_SETTINGS_MODULE=config.settings.dev
python manage.py migrate
python manage.py runserver 0.0.0.0:8000