# Architecture

## Overview

StringsRepository is a self-hosted translation management service built as a Django monolith. A single process serves both the REST API and the React SPA. There are no microservices or separate worker processes by default.

```
┌─────────────────────────────────────────────────┐
│                  Docker container                │
│                                                 │
│  ┌──────────────────────────────────────────┐   │
│  │              Gunicorn (4 workers)         │   │
│  │                                          │   │
│  │  ┌─────────────┐   ┌──────────────────┐  │   │
│  │  │  Django API  │   │  React SPA shell │  │   │
│  │  │  /api/*      │   │  all other routes│  │   │
│  │  └──────┬──────┘   └──────────────────┘  │   │
│  └─────────┼────────────────────────────────┘   │
│             │                                   │
│  ┌──────────▼──────────────────────────────┐    │
│  │          Database (SQLite / PG / MySQL)  │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

## Django Apps

| App | Responsibility |
|-----|---------------|
| `api/` | All data models, business logic, REST endpoints, authentication |
| `webui/` | Single view that renders the compiled React bundle (catch-all route) |

## Authentication

Four distinct authentication mechanisms coexist:

| Mechanism | Used by | How |
|-----------|---------|-----|
| Knox token | Web UI, main REST API | `Authorization: Token <token>` header; token stored in `localStorage` key `"auth"` |
| Project access token | CLI, Figma plugin, MCP | `Access-Token` header; handled by `AccessTokenAuth(BaseAuthentication)` in `api/views/plugin.py`; write-gated endpoints also require `WriteTokenPermission` |
| Live bundle token | Live bundle public API | `Access-Token` header; handled by `LiveBundleTokenAuth(BaseAuthentication)` in `api/views/live_bundle.py`; a single per-project token with no associated user, valid only for `/api/live-bundle/*` — see [docs/live-bundle.md](live-bundle.md) |
| Session (passkeys / 2FA) | Web UI login flows | Django session during WebAuthn and TOTP challenge/response |

Project members are assigned one of four roles (`owner`, `admin`, `editor`, `translator`) controlling what they can modify — see [docs/roles.md](roles.md).

## Rate Throttling

| Class | Scope | Key | Applied to |
|-------|-------|-----|------------|
| `LoginRateThrottle` | `login` | IP | Knox login endpoint |
| `TwoFALoginRateThrottle` | `two_fa_login` | User PK | 2FA challenge endpoint |
| `PasskeyAuthRateThrottle` | `passkey_auth` | IP | Passkey auth endpoints |
| `AICallRateThrottle` | `ai_call` | User PK | External AI/translation endpoints |

All are `SimpleRateThrottle` subclasses; rates are configured via `REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']` in settings.

## Data Model (key entities)

```
Project
  ├── Language (many)
  ├── Member (many, with role)
  ├── Token (many) — a string key
  │     └── Translation (one per language)
  ├── Scope (many) — named group with optional image
  ├── Tag (many)
  ├── Bundle (many) — versioned translation snapshot
  ├── TranslationMemory (many)
  ├── Glossary / GlossaryItem (many)
  ├── WebhookEndpoint (many)
  ├── VerificationReport (many)
  ├── ProjectAccessToken (many)
  └── LiveBundleSettings (one) — enable flag + token for public live bundle serving
User
  ├── TOTPDevice (optional)
  └── PasskeyCredential (many)
```

## API Routes

URLs are defined manually with `path()` across five modules under `api/urls/`:

| Module | Prefix | Covers |
|--------|--------|--------|
| `auth.py` | `/api/auth/` | Sign-up, login, logout, profile, password, 2FA, passkeys |
| `project.py` | `/api/project/` | Project CRUD, members, tokens, webhooks, AI settings, live bundle settings |
| `strings.py` | `/api/strings/` | Localization keys, translations, tags, bundles, glossary |
| `plugin.py` | `/api/plugin/`, `/api/mcp` | CLI/Figma push-pull, MCP endpoint |
| `live_bundle.py` | `/api/live-bundle/` | Public live bundle version/content endpoints — see [docs/live-bundle.md](live-bundle.md) |

DRF's router is intentionally not used — all views are `APIView` subclasses rather than `ModelViewSet`, so the router would add boilerplate without saving anything. The explicit `path()` list is the intended pattern.

## API Surface

All endpoints are under `/api/`. The REST API is consumed by:

- The React SPA (Knox auth)
- The CLI client (project access token)
- The Figma plugin (project access token)
- The MCP endpoint at `/api/mcp` (project access token) — see [docs/mcp.md](mcp.md)
- Client applications via the live bundle API at `/api/live-bundle/*` (live bundle token) — see [docs/live-bundle.md](live-bundle.md)

CORS is enabled only for `/api/plugin/*`, `/api/mcp`, and `/api/live-bundle/*`; the main API does not need it because the SPA is served by the same process.

## MCP Endpoint

The MCP server lives in `api/views/mcp/` as a package split by domain:

| Module | Responsibility |
|--------|---------------|
| `view.py` | `McpView` — HTTP entry point, JSON-RPC dispatch, error handling |
| `schemas.py` | `TOOLS` list (input schemas for `tools/list`) |
| `tools_project.py` | `get_project`, `get_languages` |
| `tools_tokens.py` | `list_tokens`, `get_token`, `create_token`, `set_translation`, `batch_create_tokens` |
| `tools_ai.py` | `search_similar_tokens`, `suggest_token_key`, `get_token_naming_patterns`, `check_glossary`, `suggest_translation`, `verify_string` |

`__init__.py` re-exports `McpView` so `api/urls/plugin.py` imports it unchanged.

Each tool is a plain function `(args: dict, access: ProjectAccessToken) -> dict`. `McpView._tools_call` maps tool names to functions via a static `_HANDLERS` dict and wraps every call in a uniform error boundary (`NotFoundException`, `AIProviderNotConfigured`, catch-all).

Tests mirror the same domain split under `api/tests/views/mcp/`:

| Module | Covers |
|--------|--------|
| `test_protocol.py` | Auth, `initialize`, `tools/list`, notifications, parse errors |
| `test_tools_project.py` | `get_project`, `get_languages` |
| `test_tools_tokens.py` | Token CRUD and `batch_create_tokens` |
| `test_tools_ai.py` | All AI-assist tools |
| `helpers.py` | Shared `mcp_call`, `get_result`, `get_error`, `make_ai_provider` |

## Frontend Build

The React app (TypeScript, React Router) is compiled by webpack and output to `webui/static/site/`. Django's `collectstatic` copies it into the static files directory served by gunicorn. The frontend has no separate server in production.

In development, run webpack in watch mode alongside Django's dev server.

## Database

Selected at runtime via the `DB_ENGINE` environment variable:

| `DB_ENGINE` | Database | Notes |
|-------------|----------|-------|
| `sqlite3` | SQLite | Default; suitable for single-user or small teams |
| `postgresql` | PostgreSQL 12+ | Recommended for production |
| `mysql` | MySQL 8+ / MariaDB | Supported |

The database driver is selected at Docker image build time via the `DB` build argument to keep the image lean.

## File Processors

All import/export logic lives in `api/file_processors/`. The layer is deliberately decoupled from Django's HTTP stack — writers produce raw bytes into any `BinaryIO` buffer; `FileProcessor` is the only place that creates an `HttpResponse`.

### Reading (import)

`FileImporter` accepts an uploaded file, detects its extension, and delegates to the matching reader class. All readers implement `read(file) -> list[TranslationModel]`. Readers that embed language codes in the file (xcstrings, MO) return `needs_language_code() = False`; the rest require the caller to supply a code.

### Writing (export)

`FileProcessor` is the entry point: instantiate with an `ExportFile` enum value, call `append(records, code)` for each language, then call `build_response()` to get a ready-to-return `HttpResponse`.

Each writer implements:

| Member | Description |
|--------|-------------|
| `content_type` | MIME type for the response |
| `filename` | Default download filename |
| `append(records, code)` | Accumulates records for one language |
| `write(buf)` | Serialises accumulated data to any writable buffer |

| Writer | Format | Container |
|--------|--------|-----------|
| `AndroidResourceFileWriter` | Android XML | zip |
| `AppleStringsFileWriter` | Apple `.strings` | zip |
| `XCStringsFileWriter` | Apple `.xcstrings` | zip |
| `JsonFileWriter` | Flat JSON | zip |
| `JsonDictFileWriter` | Dict JSON | zip |
| `DotNetFileWriter` | `.resx` | zip |
| `PropertiesFileWriter` | Java `.properties` | zip |
| `POFileWriter` | gettext `.po` | zip |
| `MOFileWriter` | gettext `.mo` | zip |
| `CSVFileWriter` | CSV | zip |
| `ARBFileWriter` | Flutter ARB | zip |
| `ExcelFileWriter` | Excel (one sheet per language) | xlsx |
| `ExcelSingleSheetFileWriter` | Excel (all languages, one sheet) | xlsx |

`CompareFileWriter` and `HistoryFileWriter` follow the same `write(buf)` interface but are not registered in `FileProcessor` — they are instantiated directly by their respective views.

### Adding a new format

To add a new export/import format, touch these files in order:

**Export (writing)**

1. Create `api/file_processors/<name>_file.py` implementing `content_type`, `filename`, `append(records, code)`, and `write(buf)`.
2. Add a member to `ExportFile` enum in `api/file_processors/export_file_type.py` (value = the format identifier string passed by clients), and add cases for `file_extension()` and `vendor()`.
3. Register the writer in `WRITER_MAP` in `api/file_processors/file_processor.py`.

**Import (reading)**

1. Implement `read(file) -> list[TranslationModel]` (and `needs_language_code()`) in the same or a new file.
2. Add a member to `ImportFile` enum in `api/file_processors/import_file_type.py` (value = the file extension without the dot).
3. Register the reader in `READER_MAP` in `api/file_processors/file_processor.py`, keyed by `ImportFile.<name>.name`.

## Live Bundle Cache

Generated live bundle content (see [docs/live-bundle.md](live-bundle.md)) is cached to disk under `LIVE_BUNDLE_CACHE_ROOT` (`<project_id>/<bundle_id>/<hash-of-filters>.<ext>`), separate from `MEDIA_ROOT` so it is never reachable via the `MEDIA_URL` static file route — only through the token-checked `LiveBundleContentAPI` view. Writes are atomic (temp file + `os.replace`) to avoid partial reads under concurrent requests. The cache directory is not backed by a persistent volume by default; losing it on redeploy is expected, since content regenerates from the database on the next cache miss.

## Encryption

Sensitive fields (webhook URLs, webhook auth tokens, AI provider API keys) are encrypted at rest using Django's `django-encrypted-model-fields` library, which applies AES-256 encryption keyed by `APP_SECRET_KEY`.

## Async Work

Async work runs via **Django Q** with an ORM-backed broker (`Q_CLUSTER` in settings, 2 workers, 300 s timeout, no retries). Three tasks exist:

| Task | Module | Triggered by | Notes |
|------|--------|-------------|-------|
| `run_verification_job` | `api/tasks/verification.py` | AI verification view | Processes translations in batches of 20; fires a webhook on completion; frontend polls every 5 s |
| `run_glossary_extraction_job` | `api/tasks/glossary.py` | Glossary extraction view | Capped at 200 strings; calls the configured AI provider |
| `send_webhook` | `api/tasks/webhook.py` | `dispatcher.py` on any project event; also called synchronously from the webhook verify endpoint | Signs payload with HMAC-SHA256; logs delivery result |

## Deployment

The Docker image uses a two-stage build:

1. **Node stage** — compiles the React frontend
2. **Python stage** — installs Python dependencies, copies compiled frontend, sets up entrypoint

The entrypoint runs `migrate`, `collectstatic`, optionally `createsuperuser`, then starts gunicorn on port 8080 with 4 workers.

## Security Design

- All inputs from untrusted sources are validated via Django REST Framework serialisers (allowlist approach).
- Django's ORM prevents SQL injection by default; raw queries are avoided.
- CSRF protection is enabled for session-based views.
- Outbound HTTP requests (webhook delivery, AI provider calls) use Python's `requests` library with TLS certificate verification enabled by default.
- Passwords are stored using Django's PBKDF2-SHA256 iterated hash with per-user salt.
- Webhook payloads are signed with HMAC-SHA256 so receivers can verify origin.
