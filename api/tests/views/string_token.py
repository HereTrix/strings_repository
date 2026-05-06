from django.test import TestCase

from api.models.history import HistoryRecord
from api.models.project import ProjectRole
from api.models.tag import Tag
from api.models.translations import StringToken, Translation
from api.tests.helpers import (
    add_role, authed_client, make_language, make_project, make_token,
    make_translation, make_user,
)


class StringTokenCreateTestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        self.client = authed_client(self.owner)

    def test_creates_token_and_history(self):
        resp = self.client.post('/api/string_token', {'project': self.project.pk, 'token': 'welcome', 'comment': ''}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(StringToken.objects.filter(token='welcome', project=self.project).exists())
        self.assertTrue(HistoryRecord.objects.filter(token='welcome', status=HistoryRecord.Status.created).exists())

    def test_editor_role_allowed(self):
        editor = make_user('editor')
        add_role(editor, self.project, ProjectRole.Role.editor)
        resp = authed_client(editor).post('/api/string_token', {'project': self.project.pk, 'token': 'edkey', 'comment': ''}, format='json')
        self.assertEqual(resp.status_code, 200)

    def test_translator_role_rejected(self):
        translator = make_user('translator')
        add_role(translator, self.project, ProjectRole.Role.translator)
        resp = authed_client(translator).post('/api/string_token', {'project': self.project.pk, 'token': 'tkey', 'comment': ''}, format='json')
        self.assertEqual(resp.status_code, 404)

    def test_creates_tags(self):
        resp = self.client.post('/api/string_token', {'project': self.project.pk, 'token': 'tagged', 'comment': '', 'tags': ['ios', 'android']}, format='json')
        self.assertEqual(resp.status_code, 200)
        token = StringToken.objects.get(token='tagged', project=self.project)
        tag_names = list(token.tags.values_list('tag', flat=True))
        self.assertIn('ios', tag_names)
        self.assertIn('android', tag_names)


class StringTokenDeleteTestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        self.token = make_token(self.project, 'goodbye')
        self.client = authed_client(self.owner)

    def test_deletes_token_and_records_history(self):
        resp = self.client.delete('/api/string_token', {'id': self.token.pk}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(StringToken.objects.filter(pk=self.token.pk).exists())
        self.assertTrue(HistoryRecord.objects.filter(token='goodbye', status=HistoryRecord.Status.deleted).exists())

    def test_nonexistent_token_returns_404(self):
        resp = self.client.delete('/api/string_token', {'id': 99999}, format='json')
        self.assertEqual(resp.status_code, 404)

    def test_translator_cannot_delete(self):
        translator = make_user('translator')
        add_role(translator, self.project, ProjectRole.Role.translator)
        resp = authed_client(translator).delete('/api/string_token', {'id': self.token.pk}, format='json')
        self.assertEqual(resp.status_code, 404)


class StringTokenStatusTestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        self.token = make_token(self.project, 'k')
        self.client = authed_client(self.owner)

    def test_valid_status_updated(self):
        resp = self.client.put(f'/api/string_token/{self.token.pk}/status', {'status': 'deprecated'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(StringToken.objects.get(pk=self.token.pk).status, 'deprecated')

    def test_invalid_status_returns_400(self):
        resp = self.client.put(f'/api/string_token/{self.token.pk}/status', {'status': 'gone'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_nonexistent_token_returns_404(self):
        resp = self.client.put('/api/string_token/99999/status', {'status': 'deprecated'}, format='json')
        self.assertEqual(resp.status_code, 404)


class StringTokenTagsTestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        self.token = make_token(self.project, 'k')
        old_tag, _ = Tag.objects.get_or_create(tag='old')
        self.token.tags.add(old_tag)
        self.client = authed_client(self.owner)

    def test_replaces_all_tags(self):
        resp = self.client.post(f'/api/string_token/{self.token.pk}/tags', {'tags': ['new1', 'new2']}, format='json')
        self.assertEqual(resp.status_code, 200)
        tag_names = list(self.token.tags.values_list('tag', flat=True))
        self.assertNotIn('old', tag_names)
        self.assertIn('new1', tag_names)
        self.assertIn('new2', tag_names)

    def test_nonexistent_token_returns_404(self):
        resp = self.client.post('/api/string_token/99999/tags', {'tags': []}, format='json')
        self.assertEqual(resp.status_code, 404)


class StringTokenTranslationsTestCase(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project('P', owner=self.owner)
        self.lang = make_language(self.project, 'EN')
        self.token = make_token(self.project, 'k')
        make_translation(self.token, self.lang, 'Hello')
        self.client = authed_client(self.owner)

    def test_returns_translations_per_language(self):
        resp = self.client.get(f'/api/string_token/{self.token.pk}/translations')
        self.assertEqual(resp.status_code, 200)
        import json
        data = json.loads(resp.content)['translations']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['code'], 'EN')
        self.assertEqual(data[0]['translation'], 'Hello')

    def test_nonexistent_token_returns_404(self):
        resp = self.client.get('/api/string_token/99999/translations')
        self.assertEqual(resp.status_code, 404)

    def test_language_without_translation_returns_empty_string(self):
        make_language(self.project, 'DE')
        resp = self.client.get(f'/api/string_token/{self.token.pk}/translations')
        import json
        data = json.loads(resp.content)['translations']
        de_entry = next(d for d in data if d['code'] == 'DE')
        self.assertEqual(de_entry['translation'], '')
