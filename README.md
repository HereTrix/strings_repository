![build status](https://github.com/HereTrix/strings_repository/actions/workflows/main-build.yml/badge.svg)

# StringsRepository

**StringsRepository** is a self-hosted localization management service designed to simplify translation workflows for software projects.

It provides a centralized place to manage translation keys, collaborate with translators, and synchronize translations with applications using a CLI tool or API.

## Features

* **Multiple project support** - manage translations for multiple projects independently
* **User roles & access control** - per-project roles with an invitation system for team collaboration
* **Multi-language support** - configure and manage any number of target languages per project
* **Translation management** - create, update, and track translation status for each string key
* **Plural forms** - full CLDR plural form support (zero, one, two, few, many, other)
* **Custom tags** - organize and group translations using custom tags
* **Import & export** - import/export translations in multiple supported formats
* **Translation bundles** - versioned snapshots of translations for safe production releases and rollbacks
* **Machine translation** - DeepL, Google Translate, and Generic AI (any OpenAI-compatible REST API) integration
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

## Machine Translation

DeepL, Google Translate, and any OpenAI-compatible AI provider can be configured per project to auto-translate string keys. An API key for the chosen provider is stored encrypted at rest and can be verified before use.

The **Generic AI** option lets you connect any REST-based LLM without additional dependencies. Provide an endpoint URL, a JSON payload template (using `{{text}}`, `{{target_lang}}`, and optionally `{{source_lang}}` placeholders), and a dot-notation response path to extract the translated text (e.g. `choices.0.message.content`). Built-in presets are available for OpenAI / DeepSeek, Claude, and Ollama (local).

## Configuration

Before installation, configure the required environment variables.

| Variable                    | Description                                              |
| --------------------------- | -------------------------------------------------------- |
| `APP_SECRET_KEY`            | Django secret key (any random string)                    |
| `ALLOWED_HOSTS`             | Allowed hosts separated by commas, or empty to allow all |
| `DB_ENGINE`                 | Database engine (`mysql`, `postgresql`, `sqlite3`, etc.) |
| `DB_NAME`                   | Database name                                            |
| `DB_HOST`                   | Database host (optional for SQLite)                      |
| `DB_PORT`                   | Database port (optional for SQLite)                      |
| `DB_USER`                   | Database user (optional for SQLite)                      |
| `DB_PASSWORD`               | Database password (optional for SQLite)                  |
| `DJANGO_SUPERUSER_USERNAME` | Admin username                                           |
| `DJANGO_SUPERUSER_EMAIL`    | Admin email                                              |
| `DJANGO_SUPERUSER_PASSWORD` | Admin password                                           |

For supported database engines see:
https://docs.djangoproject.com/en/5.0/ref/databases/

## Installation

### Docker

```bash
docker pull ghcr.io/heretrix/strings_repository:main
```

Run with environment variables passed directly:

```bash
docker run -d -p 8080:8080 \
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
  ghcr.io/heretrix/strings_repository:main
```

Or use an env file:

```bash
docker run -d -p 8080:8080 --env-file .env ghcr.io/heretrix/strings_repository:main
```

### Manual installation

Requires **Node.js (npm)** and **Python (pip)**.

SQLite is used by default.

```bash
cd webui
npm install
npm run build

cd ..
pip install -r requirements.txt

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
