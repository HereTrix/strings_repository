![build status](https://github.com/HereTrix/strings_repository/actions/workflows/main-build.yml/badge.svg)

# StringsRepository

**StringsRepository** is a self-hosted localization management service designed to simplify translation workflows for software projects.

It provides a centralized place to manage translation keys, collaborate with translators, and synchronize translations with applications using a CLI tool or API.

## Features

* **Multiple project support** - manage translations for multiple projects independently
* **User roles & access control** - per-project roles with an invitation system for team collaboration
* **Multi-language support** - configure and manage any number of target languages per project
* **Translation management** - create, update, and track translation status for each string key
* **Custom tags** - organize and group translations using custom tags
* **Import & export** - import/export translations in multiple supported formats
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

Then run the container with the required environment variables configured.

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
