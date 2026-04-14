from django.test import TestCase

from api.models.language import Language
from api.models.project import ProjectRole
from api.tests.helpers import (
    add_role, authed_client, make_language, make_project, make_user,
)


class LanguageAddTestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        self.client = authed_client(self.owner)

    def _post(self, code):
        return self.client.post('/api/language', {'code': code, 'project': self.project.pk}, format='json')

    def test_adds_language(self):
        resp = self._post('FR')
        self.assertEqual(resp.status_code, 204)
        self.assertTrue(Language.objects.filter(code='FR', project=self.project).exists())

    def test_code_stored_uppercase(self):
        resp = self._post('fr')
        self.assertEqual(resp.status_code, 204)
        self.assertTrue(Language.objects.filter(code='FR', project=self.project).exists())

    def test_duplicate_code_returns_400(self):
        make_language(self.project, 'DE')
        resp = self._post('DE')
        self.assertEqual(resp.status_code, 400)

    def test_admin_role_allowed(self):
        admin = make_user('admin')
        add_role(admin, self.project, ProjectRole.Role.admin)
        resp = authed_client(admin).post('/api/language', {'code': 'IT', 'project': self.project.pk}, format='json')
        self.assertEqual(resp.status_code, 204)

    def test_translator_role_rejected(self):
        translator = make_user('translator')
        add_role(translator, self.project, ProjectRole.Role.translator)
        resp = authed_client(translator).post('/api/language', {'code': 'ES', 'project': self.project.pk}, format='json')
        self.assertEqual(resp.status_code, 404)

    def test_editor_role_rejected(self):
        editor = make_user('editor')
        add_role(editor, self.project, ProjectRole.Role.editor)
        resp = authed_client(editor).post('/api/language', {'code': 'ES', 'project': self.project.pk}, format='json')
        self.assertEqual(resp.status_code, 404)


class LanguageDeleteTestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        make_language(self.project, 'JA')
        self.client = authed_client(self.owner)

    def _delete(self, code):
        return self.client.delete('/api/language', {'code': code, 'project': self.project.pk}, format='json')

    def test_deletes_language(self):
        resp = self._delete('JA')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Language.objects.filter(code='JA', project=self.project).exists())

    def test_nonexistent_language_returns_404(self):
        resp = self._delete('ZZ')
        self.assertEqual(resp.status_code, 404)

    def test_translator_cannot_delete(self):
        translator = make_user('translator')
        add_role(translator, self.project, ProjectRole.Role.translator)
        resp = authed_client(translator).delete('/api/language', {'code': 'JA', 'project': self.project.pk}, format='json')
        self.assertEqual(resp.status_code, 404)
