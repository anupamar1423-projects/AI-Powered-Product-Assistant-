#!/usr/bin/env bash
set -o errexit

python manage.py migrate --noinput
python manage.py seed_data
python manage.py bootstrap_deploy_admin

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-10000}" \
  --workers 1 \
  --timeout 120
