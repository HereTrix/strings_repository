import io
from django.test import TestCase

from api.models.translations import StringToken, Translation
from api.tests.helpers import (
    authed_client, make_language, make_project, make_user,
)


def _strings_file(content):
    """Return an in-memory .strings file-like object."""
    buf = io.BytesIO(content.encode())
    buf.name = 'en.strings'
    return buf


def _json_file(content, name='en.json'):
    buf = io.BytesIO(content.encode())
    buf.name = name
    return buf


class ImportAPITestCase(TestCase):

    def setUp(self):
        self.user = make_user('owner')
        self.project = make_project('P', owner=self.user)
        make_language(self.project, 'EN')
        self.client = authed_client(self.user)

    def test_import_strings_file_creates_tokens_and_translations(self):
        content = '"welcome" = "Hello";\n"goodbye" = "Bye";\n'
        resp = self.client.post('/api/import', {
            'project_id': self.project.pk,
            'code': 'EN',
            'file': _strings_file(content),
        }, format='multipart')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(StringToken.objects.filter(token='welcome', project=self.project).exists())
        self.assertTrue(StringToken.objects.filter(token='goodbye', project=self.project).exists())
        self.assertTrue(
            Translation.objects.filter(
                token__token='welcome',
                language__code='EN',
                translation='Hello'
            ).exists()
        )

    def test_import_without_file_returns_400(self):
        resp = self.client.post('/api/import', {
            'project_id': self.project.pk,
            'code': 'EN',
        }, format='multipart')
        self.assertEqual(resp.status_code, 400)

    def test_import_without_project_id_returns_400(self):
        resp = self.client.post('/api/import', {
            'code': 'EN',
            'file': _strings_file('"k" = "v";\n'),
        }, format='multipart')
        self.assertEqual(resp.status_code, 400)

    def test_import_assigns_tags(self):
        content = '"tagged_key" = "Tagged value";\n'
        resp = self.client.post('/api/import', {
            'project_id': self.project.pk,
            'code': 'EN',
            'tags': 'ios',
            'file': _strings_file(content),
        }, format='multipart')
        self.assertEqual(resp.status_code, 200)
        token = StringToken.objects.get(token='tagged_key', project=self.project)
        self.assertIn('ios', list(token.tags.values_list('tag', flat=True)))

    def test_import_unauthenticated_returns_401(self):
        from rest_framework.test import APIClient
        resp = APIClient().post('/api/import', {
            'project_id': self.project.pk,
            'code': 'EN',
            'file': _strings_file('"k" = "v";\n'),
        }, format='multipart')
        self.assertEqual(resp.status_code, 401)

    def test_import_updates_existing_translation(self):
        from api.models.translations import StringToken, Translation
        from api.models.language import Language
        token = StringToken.objects.create(token='key', project=self.project)
        lang = Language.objects.get(code='EN', project=self.project)
        Translation.objects.create(token=token, language=lang, translation='Old')

        content = '"key" = "Updated";\n'
        resp = self.client.post('/api/import', {
            'project_id': self.project.pk,
            'code': 'EN',
            'file': _strings_file(content),
        }, format='multipart')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            Translation.objects.get(token=token, language=lang).translation,
            'Updated'
        )
