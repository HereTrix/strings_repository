import json
import zipfile
import io
from django.test import TestCase

from api.tests.helpers import (
    authed_client, make_language, make_project, make_token,
    make_translation, make_user,
)


class ExportFormatsAPITestCase(TestCase):

    def test_returns_list_of_formats(self):
        from rest_framework.test import APIClient
        resp = APIClient().get('/api/supported_formats')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 0)
        for fmt in data:
            self.assertIn('type', fmt)
            self.assertIn('name', fmt)
            self.assertIn('extension', fmt)


class ExportAPITestCase(TestCase):

    def setUp(self):
        self.user = make_user('owner')
        self.project = make_project('P', owner=self.user)
        self.lang = make_language(self.project, 'EN')
        self.token = make_token(self.project, 'greeting')
        make_translation(self.token, self.lang, 'Hello')
        self.client = authed_client(self.user)

    def test_export_strings_format_returns_zip(self):
        resp = self.client.get('/api/export', {
            'project_id': self.project.pk,
            'type': 'strings',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn('zip', resp.get('Content-Type', ''))

    def test_export_with_specific_code(self):
        resp = self.client.get('/api/export', {
            'project_id': self.project.pk,
            'type': 'strings',
            'codes': 'EN',
        })
        self.assertEqual(resp.status_code, 200)
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = zf.namelist()
        self.assertTrue(any('en' in n.lower() for n in names))

    def test_export_unauthenticated_returns_401(self):
        from rest_framework.test import APIClient
        resp = APIClient().get('/api/export', {
            'project_id': self.project.pk,
            'type': 'strings',
        })
        self.assertEqual(resp.status_code, 401)

    def test_export_filters_by_tag(self):
        from api.models.tag import Tag
        tag, _ = Tag.objects.get_or_create(tag='mobile')
        self.token.tags.add(tag)

        other_token = make_token(self.project, 'other_key')
        make_translation(other_token, self.lang, 'Other')

        resp = self.client.get('/api/export', {
            'project_id': self.project.pk,
            'type': 'strings',
            'tags': 'mobile',
        })
        self.assertEqual(resp.status_code, 200)
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        content = zf.read(zf.namelist()[0]).decode()
        self.assertIn('greeting', content)
        self.assertNotIn('other_key', content)
