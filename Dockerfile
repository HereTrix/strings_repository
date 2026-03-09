# ──────────────────────────────────────────────
# Stage 1: Frontend build
# ──────────────────────────────────────────────
FROM node:25.8-alpine AS frontend
WORKDIR /app/webui
COPY ./webui/package*.json ./
RUN npm ci
COPY ./webui/ ./
RUN npm run build

# ──────────────────────────────────────────────
# Stage 2: Backend / final image
# ──────────────────────────────────────────────
FROM python:3.14.3-alpine AS backend
WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY --chown=1000:1000 . /app/

# Copy frontend build output from stage 1 (bundles + HTML template)
COPY --from=frontend --chown=1000:1000 /app/webui/static/ /app/webui/static/
COPY --from=frontend --chown=1000:1000 /app/webui/templates/ /app/webui/templates/

RUN mkdir -p /app/static && chown -R 1000:1000 /app

USER 1000:1000

EXPOSE 8080

CMD python manage.py collectstatic --noinput \
    && python manage.py migrate \
    && (python manage.py createsuperuser --noinput || true) \
    && gunicorn repository.wsgi:application --bind 0.0.0.0:8080 --workers 4

HEALTHCHECK --interval=30s --timeout=3s \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1