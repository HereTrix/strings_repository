#!/bin/sh
set -e

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Collecting static..."
python manage.py collectstatic --noinput

# optional: create superuser only if env provided
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "Creating superuser..."
  python manage.py createsuperuser \
    --noinput \
    || true
fi

echo "Starting qcluster..."
python manage.py qcluster &

echo "Starting gunicorn..."
exec gunicorn repository.wsgi:application \
  --bind 0.0.0.0:8080 \
  --workers 4 \
  --timeout 60 \
  --access-logfile -