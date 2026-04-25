# api/

Django app containing all data models, REST views, serializers, and business logic.

## Structure

```
api/
  models/               # one file per model group, all re-exported via __init__.py
  views/                # one file per resource group
  serializers/          # one file per resource group
  filters/              # django-filter FilterSet subclasses
  file_processors/      # strategy pattern: one class per import/export format
  translation_providers/ # DeepL, Google, Generic AI
  paginators/
  migrations/           # sequential numbered, 0001–0017
  crypto.py             # Fernet encryption (webhook URLs, API keys, access tokens)
  dispatcher.py         # webhook dispatch via daemon threads (no task queue)
  urls.py
```

## Models

All models imported through `api/models/__init__.py`. Add new models there.

Key models and their constraints:
- `StringToken`: `unique_together = ['token', 'project']`, status `active`/`deprecated`, M2M to `Tag` and `Scope`
- `Translation`: `unique_together = ['token', 'language']`, status `new`/`in_review`/`approved`/`deprecated`. Business logic lives in `create_or_update_translation()` static method on the model.
- `PluralTranslation`: FK to `Translation`, CLDR forms (`zero`, `one`, `two`, `few`, `many`, `other`)
- `ProjectRole.Role`: `owner`, `admin`, `editor`, `translator`. Role capability lists are class-level attributes (e.g., `change_token_roles`). Use these lists for permission checks, not raw string comparisons.
- `ProjectAccessToken`: has `permission` (read/write) and optional `expiration`
- `TranslationIntegration`: machine translation provider + encrypted API key (`BinaryField`)
- `WebhookEndpoint`: URL and auth token stored encrypted as `BinaryField` via `crypto.py`; `signing_secret` is auto-generated HMAC-SHA256 hex

## Views

All views extend DRF `generics.*` CBVs. Permission/role checks are done by filtering querysets with `roles__user=user` and `roles__role__in=ProjectRole.<role_list>`.

Plugin views (`views/plugin.py`) use `permission_classes = [AllowAny]` and validate the `Access-Token` header manually via `validate_access_token()` helper.

MCP view (`views/mcp.py`) is a plain Django `View` (not DRF), implementing JSON-RPC 2.0 over HTTP POST.

## Serializers

Standard DRF `ModelSerializer`. `api_key` fields are `write_only=True`. `ProjectParticipantsSerializer` is a plain class with a static `serialize()` method — not a DRF subclass.

## Filters

`StringTokenFilter` supports: `q` (searches key name and translation text), `tags` (comma-separated), `new`, `untranslated`, `status`, `scope`. Use `django-filter` `FilterSet` pattern for new filters.

## Pagination

`TranslationsPagination`: `LimitOffsetPagination`, `default_limit=50`, `max_limit=200`, returns `{count, results}`.

## File Processors

Strategy pattern. `FileProcessor` holds a `WRITER_MAP` and `FileImporter` holds a `READER_MAP` — both map format enums to processor classes. Formats: `.strings`, `.xcstrings`, `.xml` (Android), `.xlsx`, `.json`, `.json` (dict), `.resx`, `.properties`, `.po`, `.mo`.

## Encryption

`api/crypto.py` uses `cryptography.Fernet` keyed from SHA-256 of Django's `SECRET_KEY`. Sensitive fields (`WebhookEndpoint.url`, `WebhookEndpoint.auth_token`, `TranslationIntegration.api_key`, `ProjectAccessToken` values) are stored as `BinaryField` and must be encrypted/decrypted through this module.

## Webhook Dispatch

`api/dispatcher.py` fires webhooks in daemon threads — no Celery or task queue. HMAC-SHA256 signature sent in `X-Signature` header.

## Migrations

Sequential numbered (`0001`–`0017`). Always generate with `makemigrations` and review before committing. Never hand-edit migration files.

## Tests

Under `api/tests/`, mirroring the source structure. Run with `python manage.py test api`.
