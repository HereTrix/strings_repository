# StringsRepository

A self-hosted localization management platform. Stores translation keys (string tokens) across projects and languages, and exposes them to clients via REST API, CLI, Figma plugin, and MCP endpoint.

## Architecture

Django monolith serving two things from a single process:
- REST API at `/api/` (Django REST Framework, Knox token auth)
- React SPA at all other routes (catch-all Django view renders the compiled bundle)

Two Django apps: `api/` (all data and logic) and `webui/` (only serves the SPA shell).

## Auth

- Web UI and API: Knox token auth. Token stored in `localStorage` key `"auth"`, sent as `Authorization` header.
- CLI / Figma plugin / MCP: `ProjectAccessToken` model, sent as `Access-Token` header. Views using this auth set `permission_classes = [AllowAny]` and validate the token manually.

## Database

SQLite by default. PostgreSQL (`psycopg`) and MySQL (`mysqlclient`) supported via `DB_ENGINE` env var. Driver selection at Docker build time via `DB` build arg.

## Environment

Config via `django-environ`. Key env vars: `APP_SECRET_KEY`, `DB_ENGINE`, `DB_NAME`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`. Falls back to `os.environ` if no `.env` file exists.

## Running

Docker: two-stage build (Node for frontend, Python for backend). Entrypoint runs `migrate`, `collectstatic`, optional `createsuperuser`, then gunicorn on port `8080` with 4 workers.

Dev: run Django and webpack separately. Webpack watch mode outputs to `webui/static/site/` which Django serves.

## CORS

Only enabled for plugin and MCP endpoints (`/api/plugin/*` and `/api/mcp`). The main web API does not need CORS because the SPA is served by the same Django process.
