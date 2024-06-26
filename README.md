![build status](https://github.com/HereTrix/strings_repository/actions/workflows/main-build.yml/badge.svg)

StringsRepository
========

**StringsRepository** is a self-hosted web-service that simplifies software localization management between different platforms. 

Overview
--------

**StringsRepository** provides the following features:

* Multiple project support
* User roles for each project
* Custom tags for translations separation
* Export translations to file
* Full history of changes
* Import translations from file
* [Figma plugin](https://github.com/HereTrix/strings_repository-figma-plugin) support
* [CLI application](https://github.com/HereTrix/strings_repository_cli) for CI/CD purposes

Configuration
--------

Befor installation please ensure all OS variables are set.

List of variables:
- `APP_SECRET_KEY` - secret key (any random string)
- `ALLOWED_HOSTS` - allowed hosts separated by comma or empty to allow all
- `DB_ENGINE` - engine name (mysql, postgresql, sqlite3, [etc.](https://docs.djangoproject.com/en/5.0/ref/databases/)
- `DB_NAME` - database name
- `DB_HOST` - database host (can be skipped for sqlite3)
- `DB_PORT` - database port (can be skipped for sqlite3)
- `DB_USER` - database user (can be skipped for sqlite3)
- `DB_PASSWORD` - password for database (can be skipped for sqlite3)
- `DJANGO_SUPERUSER_USERNAME` - the superuser login name
- `DJANGO_SUPERUSER_EMAIL` - the superuser email
- `DJANGO_SUPERUSER_PASSWORD` - the superuser password


Installation
--------

### Docker

`docker pull ghcr.io/heretrix/strings_repository:main`

### Manual installation

The application require `npm` to be installed.

The application uses SQLite storage by default. If you want to use own database update `DATABASES` section in `settings.py`

```
cd ./webui
npm i
npm run build
cd ..
pip install -r requirements.txt
python manage.py makemigrations api
python manage.py migrate
```

Do not forget to create superuser by `python manage.py createsuperuser`

Docker file will be added in future updates

How to use
=======
You can find instructions on [wiki page](https://github.com/HereTrix/strings_repository/wiki)

License
-------

**StringsRepository** is released under the MIT license. See `LICENSE` for details.
