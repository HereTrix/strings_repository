StringsRepository
========

**StringsRepository** is an self-hosted solution that simplifies localization management between different platforms. 

Overview
--------

**StringsRepository** provides the following features:

* Multiple project support
* User roles for each project
* Custom tags for translations separation
* Export translations to file
* Full history of changes
* Import translations from file
* [Figma plugin support](https://github.com/HereTrix/strings_repository-figma-plugin)

Configuration
--------

Befor installation please ensure all OS variables are set.

List of variables:
- APP_SECRET_KEY - secret key
- ALLOWED_HOSTS - allowed hosts separated by comma
- DB_ENGINE - engine name
- DB_NAME - database name
- DB_HOST - database host (can be skipped for sqlite3)
- DB_PORT - database port (can be skipped for sqlite3)
- DB_USER - database user (can be skipped for sqlite3)
- DB_PASSWORD - password for database (can be skipped for sqlite3)


Installation
--------

The application require `npm` to be installed.

The application uses SQLite storage. If you want to use own database update `DATABASES` section in `settings.py`

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

License
-------

**StringsRepository** is released under the MIT license. See `LICENSE` for details.