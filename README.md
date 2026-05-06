![build status](https://github.com/HereTrix/strings_repository/actions/workflows/main-build.yml/badge.svg)

# StringsRepository

**StringsRepository** is a self-hosted translation management service for product teams that want full control without the complexity of a general-purpose platform. It's designed around an API/CLI-first workflow: translators work in the UI, developers push and pull strings from CI. Deploy it in a single Docker container, own the data, and extend the code directly.

## Features

* **Multiple project support** - manage translations for multiple projects independently
* **User roles & access control** - per-project roles with an invitation system for team collaboration
* **Multi-language support** - configure and manage any number of target languages per project
* **Translation management** - create, update, and track translation status for each string key
* **Plural forms** - full CLDR plural form support (zero, one, two, few, many, other)
* **Custom tags** - organize and group translations using custom tags
* **Scopes** - group string keys into named scopes with optional context images; translators browse translations by scope in a visual gallery
* **Import & export** - import/export translations in multiple supported formats
* **Translation bundles** - versioned snapshots of translations for safe production releases and rollbacks
* **Machine translation** - DeepL, Google Translate, and Generic AI (any OpenAI-compatible REST API) integration
* **AI translation verification** - async quality audits powered by any OpenAI-compatible or Anthropic-compatible provider; source quality and translation accuracy modes with per-check selection, scope/tag filtering, suggestion review, and one-click apply
* **Two-factor authentication (2FA)** - TOTP-based 2FA per user account; project owners can require 2FA for all project members
* **Glossary** - manage domain-specific terms with definitions and per-language preferred translations; AI-powered term extraction from existing strings; import/export support
* **Translation memory** - automatically surface previously-translated strings similar to the current source text to improve consistency
* **Passkeys (WebAuthn)** - passwordless authentication via FIDO2/passkeys as an alternative to passwords
* **MCP support** - AI-agent integration via Model Context Protocol for IDE-based key management and localization workflows
* **Webhooks** - real-time event notifications to external services
* **Full change history** - track all translation changes with an exportable history log
* **Figma plugin** - integrate design workflows
  https://github.com/HereTrix/strings_repository-figma-plugin
* **CLI application** - integrate localization into CI/CD pipelines
  https://github.com/HereTrix/strings_repository_cli

## Tech Stack

| Layer          | Technology                                                                  |
| -------------- | --------------------------------------------------------------------------- |
| Backend        | Python / Django REST Framework                                              |
| Authentication | Knox token-based authentication                                             |
| Frontend       | React (TypeScript) with React Router                                        |
| Database       | SQLite (default) or any Django-supported database (PostgreSQL, MySQL, etc.) |
| Deployment     | Docker                                                                      |

## Supported File Formats

| Type value     | Format                        | Extension     |
| -------------- | ----------------------------- | ------------- |
| `strings`      | Apple (.strings)              | `.strings`    |
| `xcstrings`    | Apple Xcode (.xcstrings)      | `.xcstrings`  |
| `xml`          | Android                       | `.xml`        |
| `excel`        | Excel (separate sheets)       | `.xlsx`       |
| `xlsx`         | Excel (single sheet)          | `.xlsx`       |
| `json`         | JSON — Key/Value (i18next)    | `.json`       |
| `json_dict`    | JSON — Key/Dictionary         | `.json`       |
| `resx`         | ASP.NET                       | `.resx`       |
| `properties`   | Java                          | `.properties` |
| `po`           | Portable Object               | `.po`         |
| `mo`           | Binary MO                     | `.mo`         |
| `csv`          | CSV                           | `.csv`        |

## Translation Bundles

Bundles are versioned snapshots of all project translations. They allow you to:

* Pin a specific translation state for a production release
* Roll back to a previous version by comparing and reviewing changes
* Test a specific version in QA without affecting live data

### How it works

1. **Create a bundle** — takes a point-in-time snapshot of all current translations across all languages. Version names are auto-generated (`v1`, `v2`, …) or you can provide a custom name (e.g. `release-2.1.0`).
2. **Activate a bundle** — marks it as the production bundle for the project. Only one bundle can be active at a time; activating a new one automatically deactivates the previous.
3. **Compare bundles** — diff any two bundles or compare a bundle against live translations to review what has changed, been added, or removed.
4. **Export from a bundle** — generate platform-specific files from any bundle snapshot in any supported format.

### Plugin / CLI integration

The export endpoint accepts an optional `bundle_version` field to control which translation source is used:

| `bundle_version` value | Behavior                                         | Use case                  |
| ---------------------- | ------------------------------------------------ | ------------------------- |
| omitted or `"live"`    | Live translations (latest edits in the database) | Local development         |
| `"active"`             | Currently active bundle                          | Production CI/CD          |
| `"v3"` (any name)      | That specific bundle                             | QA, rollback verification |

If `bundle_version='active'` is requested and no bundle is active, the API returns `404` with an explicit error message.

The version names `active` and `live` are reserved and cannot be used as bundle names.

## Webhooks

Webhooks allow external services to receive real-time notifications when events occur in a project.

### Configuration

Each webhook endpoint is configured with:

* **URL** — the destination endpoint (stored encrypted at rest)
* **Events** — one or more event types to subscribe to
* **Auth token** (optional) — sent as `Authorization: Bearer <token>` (stored encrypted at rest)
* **Template** (optional) — a Jinja-style text template for the payload body (e.g. for Slack/Teams integrations)
* **Signing secret** — auto-generated HMAC-SHA256 secret sent in the `X-Signature` header for payload verification

### Supported events

| Event                      | Triggered when                              |
| -------------------------- | ------------------------------------------- |
| `translation.created`      | A new translation is added                  |
| `translation.updated`      | A translation value is changed              |
| `translation.status_changed` | A translation status changes              |
| `token.created`            | A new string key is created                 |
| `token.deleted`            | A string key is deleted                     |
| `token.status_changed`     | A string key status changes                 |
| `language.added`           | A language is added to the project          |
| `language.removed`         | A language is removed from the project      |
| `import.completed`         | A file import completes                     |
| `member.invited`           | A team member is invited                    |
| `member.role_changed`      | A team member's role is changed             |
| `verification.completed`   | An AI verification job finishes (any status) |

## MCP Integration

StringsRepository exposes a [Model Context Protocol](https://modelcontextprotocol.io) endpoint at `POST /api/mcp`, enabling AI agents and IDE assistants (Claude Code, Cursor, VS Code) to manage localization keys without leaving the editor.

### Authentication

The endpoint uses project access tokens — the same tokens used by the CLI. Pass the token in the `Access-Token` request header.

### Available tools

| Tool | Description |
| ---- | ----------- |
| `get_project` | Get project info for the configured token |
| `get_languages` | List all configured language codes |
| `list_tokens` | List/search localization keys (by name or translation text) |
| `get_token` | Get a key with all its translations across every language |
| `create_token` | Create a new localization key |
| `set_translation` | Create or update a translation for a key and language |
| `search_similar_tokens` | Find existing keys similar to a given text (duplicate prevention) |
| `suggest_token_key` | Suggest a key name derived from source text |
| `get_token_naming_patterns` | Analyse the project's key naming conventions |
| `batch_create_tokens` | Create multiple keys with translations in one call |
| `check_glossary` | Check whether words or phrases in a source string match project glossary terms; returns matched terms with definitions and preferred translations |
| `suggest_translation` | Fetch translation memory suggestions — previously-translated strings whose source text is similar to the given input |
| `verify_string` | Run AI quality verification on a single source/translation pair (requires an AI provider configured on the project); returns severity, suggested correction, and reason |

### IDE setup (Claude Code)

Create a project access token in the StringsRepository web UI, then add the server to your MCP configuration:

```json
{
  "mcpServers": {
    "strings-repository": {
      "type": "http",
      "url": "https://your-server/api/mcp",
      "headers": {
        "Access-Token": "your-project-access-token"
      }
    }
  }
}
```

### IDE setup via CLI proxy (stdio)

If your IDE only supports stdio MCP transport, use the CLI in proxy mode after configuring it with your server URL and token:

```bash
strings mcp
```

See the [CLI repository](https://github.com/HereTrix/strings_repository_cli) for setup details.

## Machine Translation

DeepL, Google Translate, and any OpenAI-compatible AI provider can be configured per project to auto-translate string keys. An API key for the chosen provider is stored encrypted at rest and can be verified before use.

The **Generic AI** option lets you connect any REST-based LLM without additional dependencies. Provide an endpoint URL, a JSON payload template (using `{{text}}`, `{{target_lang}}`, and optionally `{{source_lang}}` placeholders), and a dot-notation response path to extract the translated text (e.g. `choices.0.message.content`). Built-in presets are available for OpenAI / DeepSeek, Claude, and Ollama (local).

## Two-Factor Authentication (2FA)

Users can enable TOTP-based 2FA on their account via **Profile → Security**. Any standard authenticator app (Google Authenticator, Authy, etc.) can be used to scan the QR code. Backup codes are generated at setup time.

Project owners can enforce 2FA across their entire team. When enabled, any member without active 2FA will receive a `403` on all project API calls until they complete setup. The requirement can be toggled in **Project → Info → Security Settings**.

## AI Translation Verification

AI verification runs quality audits on your translations using any OpenAI-compatible or Anthropic-compatible provider (including self-hosted models via a custom endpoint URL). The provider is configured per-project in **Project → Info → AI Provider**.

### Modes

| Mode | What is checked | Target language required |
| ---- | --------------- | ------------------------ |
| **Source Quality** | Source/default language strings for spelling, grammar, tone, punctuation, capitalisation, and placeholder format | No |
| **Translation Accuracy** | Translations from the source language to a selected target language for semantic accuracy, placeholder preservation, omissions/additions, grammar, and tone match | Yes |

### How it works

1. **Configure an AI provider** — go to **Project → Info → AI Provider**, select a provider type (OpenAI-compatible or Anthropic-compatible), enter the model name and API key. Leave the endpoint URL blank to use the default. Built-in presets are available for OpenAI, Claude, and Ollama.
2. **Run a verification** — in the **Verify** tab, click **Run Verification**. Select a mode, optionally filter by scope, tags, or "new only" (Mode 2), choose which checks to include, and click **Estimate strings** to preview API token usage before submitting.
3. **Review results** — the job runs asynchronously; the tab polls for status every 5 seconds. Each result row shows a severity badge (`ok` / `warning` / `error`), a word-level diff of the current value vs. the AI suggestion, and the reason.
4. **Apply suggestions** — editors, admins, and owners can select individual suggestions, adjust the text inline, and apply them as standard translation updates with full history tracking. Applying any suggestion marks the report read-only.
5. **Comment** — any project member can add comments to individual suggestions for discussion.

Reports are capped per project (default: 10; configurable by the project owner). When the cap is reached, the oldest report is deleted automatically. Admins and owners can delete any report manually. A `verification.completed` webhook event fires when each job finishes.

## Configuration

Before installation, configure the required environment variables.

| Variable                    | Description                                              |
| --------------------------- | -------------------------------------------------------- |
| `APP_SECRET_KEY`            | Django secret key (any random string)                    |
| `ALLOWED_HOSTS`             | Allowed hosts separated by commas, or empty to allow all |
| `DB_ENGINE`                 | Database engine — see table below                        |
| `DB_NAME`                   | Database name (or file path for SQLite)                  |
| `DB_HOST`                   | Database host (not required for SQLite)                  |
| `DB_PORT`                   | Database port (not required for SQLite)                  |
| `DB_USER`                   | Database user (not required for SQLite)                  |
| `DB_PASSWORD`               | Database password (not required for SQLite)              |
| `DJANGO_SUPERUSER_USERNAME` | Admin username                                           |
| `DJANGO_SUPERUSER_EMAIL`    | Admin email                                              |
| `DJANGO_SUPERUSER_PASSWORD` | Admin password                                           |
| `WEBAUTHN_RP_ID`            | Webauth ID (your domain)                                 |
| `WEBAUTHN_RP_NAME`          | Webauth display name (StringsRepository by default)      |

### Supported databases

| `DB_ENGINE` value | Database             | Driver (bundled)         |
| ----------------- | -------------------- | ------------------------ |
| `sqlite3`         | SQLite               | built-in                 |
| `postgresql`      | PostgreSQL 12+       | `psycopg` (v3)           |
| `mysql`           | MySQL 8+ / MariaDB   | `mysqlclient`            |

## Installation

### Docker

```bash
docker pull ghcr.io/heretrix/strings_repository:main
```

#### Building a leaner image

By default the image bundles drivers for all supported databases. If you build the image yourself you can include only the driver you need via the `DB` build argument:

| `DB` value     | Installed drivers         | Use when               |
| -------------- | ------------------------- | ---------------------- |
| `all` (default)| PostgreSQL + MySQL        | pre-built / unknown    |
| `sqlite`       | none (built-in)           | SQLite only            |
| `postgresql`   | psycopg (v3)              | PostgreSQL             |
| `mysql`        | mysqlclient               | MySQL / MariaDB        |

```bash
# PostgreSQL-only image (~30 MB smaller than the default)
docker build --build-arg DB=postgresql -t strings-repository .

# MySQL/MariaDB-only image
docker build --build-arg DB=mysql -t strings-repository .

# SQLite only (smallest image, no native libraries)
docker build --build-arg DB=sqlite -t strings-repository .
```

The pre-built image published to `ghcr.io` always uses `DB=all` so no rebuild is needed when pulling it.

#### docker run

Run with environment variables passed directly:

```bash
docker run -d -p 8080:8080 \
  -v media_data:/app/media \
  -e APP_SECRET_KEY=your-secret-key \
  -e ALLOWED_HOSTS=yourdomain.com \
  -e DB_ENGINE=postgresql \
  -e DB_NAME=stringsdb \
  -e DB_HOST=db \
  -e DB_PORT=5432 \
  -e DB_USER=dbuser \
  -e DB_PASSWORD=dbpassword \
  -e DJANGO_SUPERUSER_USERNAME=admin \
  -e DJANGO_SUPERUSER_EMAIL=admin@example.com \
  -e DJANGO_SUPERUSER_PASSWORD=adminpassword \
  -e WEBAUTHN_RP_ID=your.domain \
  -e WEBAUTHN_RP_NAME=StringsRepository \
  ghcr.io/heretrix/strings_repository:main
```

The `-v media_data:/app/media` mount keeps uploaded scope images and other user files across container updates. Without it uploads are lost when the container is replaced.

Or use an env file:

```bash
docker run -d -p 8080:8080 -v media_data:/app/media --env-file .env ghcr.io/heretrix/strings_repository:main
```

### Manual installation

Requires **Node.js (npm)** and **Python (pip)**.

```bash
cd webui
npm install
npm run build

cd ..
pip install -r requirements.txt
```

Then install the driver for your database (SQLite needs none — it is built into Python):

```bash
# PostgreSQL
pip install -r requirements-postgresql.txt

# MySQL / MariaDB
pip install -r requirements-mysql.txt
```

```bash
python manage.py makemigrations api
python manage.py migrate
python manage.py createsuperuser
```

## Usage

Detailed usage instructions are available in the project wiki:

https://github.com/HereTrix/strings_repository/wiki

## Related Tools

* CLI client
  https://github.com/HereTrix/strings_repository_cli

* Figma plugin
  https://github.com/HereTrix/strings_repository-figma-plugin

## License

StringsRepository is released under the **MIT License**.
See the `LICENSE` file for details.
