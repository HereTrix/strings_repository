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
FROM python:3.14.4-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TMPDIR=/app/tmp

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY --chown=1000:1000 . /app/

# Copy frontend build output from stage 1 (bundles + HTML template)
COPY --from=frontend --chown=1000:1000 /app/webui/static/ /app/webui/static/
COPY --from=frontend --chown=1000:1000 /app/webui/templates/ /app/webui/templates/

RUN mkdir -p /app/static /app/tmp \
    && chmod -R 777 /app/tmp /app/static

# entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]

HEALTHCHECK --interval=30s --timeout=3s \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1