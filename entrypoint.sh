#!/bin/bash
set -e

echo "Running collectstatic..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
exec gunicorn wms_core.wsgi:application --bind 0.0.0.0:8000 --workers 3 --access-logfile -