#!/usr/bin/env sh
set -e

echo "[entrypoint] migrate"
python manage.py migrate --noinput

echo "[entrypoint] collectstatic"
python manage.py collectstatic --noinput

echo "[entrypoint] start gunicorn"
exec gunicorn sistemakontrol.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 3 \
  --log-level info
