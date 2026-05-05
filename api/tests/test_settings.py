from django.test import TestCase
from django.conf import settings


class SettingsSecurityTest(TestCase):

    def test_debug_is_false_by_default(self):
        self.assertFalse(settings.DEBUG)

    def test_csrf_middleware_present(self):
        self.assertIn(
            'django.middleware.csrf.CsrfViewMiddleware',
            settings.MIDDLEWARE,
        )

    def test_csrf_after_session_middleware(self):
        mw = settings.MIDDLEWARE
        session_idx = mw.index('django.contrib.sessions.middleware.SessionMiddleware')
        csrf_idx = mw.index('django.middleware.csrf.CsrfViewMiddleware')
        self.assertGreater(csrf_idx, session_idx)

    def test_common_middleware_not_duplicated(self):
        count = settings.MIDDLEWARE.count('django.middleware.common.CommonMiddleware')
        self.assertLessEqual(count, 1)

    def test_null_not_in_cors_origins(self):
        self.assertNotIn('null', settings.CORS_ALLOWED_ORIGINS)

    def test_wildcard_not_in_allowed_hosts_default(self):
        # When ALLOWED_HOSTS env var is absent, default is localhost/127.0.0.1, not '*'
        import os
        from repository.app_env import env_value
        raw = os.environ.get('ALLOWED_HOSTS', '')
        if not raw:
            self.assertNotIn('*', settings.ALLOWED_HOSTS)
