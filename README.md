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
* Import translations from file

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