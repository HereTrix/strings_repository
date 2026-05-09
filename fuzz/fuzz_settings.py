"""Minimal Django settings for fuzz targets."""

SECRET_KEY = 'fuzz-only-insecure-key-not-for-production'
DEBUG = False
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'api',
]
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True
