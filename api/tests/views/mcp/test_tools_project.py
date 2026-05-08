from django.test import TestCase, Client

from api.tests.helpers import make_access_token, make_language, make_project, make_user
from .helpers import get_result, mcp_call


class ProjectToolsTestCase(TestCase):

    def setUp(self):
        self.user = make_user('dev')
        self.project = make_project('MyApp', owner=self.user)
        make_language(self.project, 'EN')
        make_language(self.project, 'FR')
        self.access = make_access_token(self.project, self.user)
        self.client = Client()

    # ── get_project ───────────────────────────────────────────────────────────

    def test_get_project_returns_project_info(self):
        result = get_result(mcp_call(self.client, self.access, 'get_project', {}))
        self.assertEqual(result['name'], 'MyApp')
        self.assertEqual(result['id'], self.project.id)

    # ── get_languages ─────────────────────────────────────────────────────────

    def test_get_languages_returns_codes(self):
        result = get_result(mcp_call(self.client, self.access, 'get_languages', {}))
        self.assertIn('EN', result['languages'])
        self.assertIn('FR', result['languages'])
