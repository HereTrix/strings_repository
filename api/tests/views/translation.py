import json
from django.test import TestCase

from api.models.history import HistoryRecord
from api.models.translations import Translation
from api.tests.helpers import (
    add_role, authed_client, make_language, make_project, make_token,
    make_translation, make_user,
)


class TranslationAPITestCase(TestCase):

    def setUp(self):
        self.user = make_user('editor')
        self.project = make_project('Proj', owner=self.user)
        self.lang = make_language(self.project, 'EN')
        self.token = make_token(self.project, 'greeting')
        self.client = authed_client(self.user)

    def _post(self, data):
        return self.client.post('/api/translation', data, format='json')

    def test_creates_translation(self):
        resp = self._post({'project_id': self.project.pk, 'code': 'EN', 'token': 'greeting', 'translation': 'Hello'})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Translation.objects.filter(token=self.token, language=self.lang).exists())

    def test_updates_existing_translation(self):
        make_translation(self.token, self.lang, 'Old')
        resp = self._post({'project_id': self.project.pk, 'code': 'EN', 'token': 'greeting', 'translation': 'New'})
        self.assertEqual(resp.status_code, 200)
        tr = Translation.objects.get(token=self.token, language=self.lang)
        self.assertEqual(tr.translation, 'New')
        self.assertEqual(tr.status, Translation.Status.in_review)

    def test_same_text_does_not_create_history_record(self):
        make_translation(self.token, self.lang, 'Same')
        before = HistoryRecord.objects.count()
        self._post({'project_id': self.project.pk, 'code': 'EN', 'token': 'greeting', 'translation': 'Same'})
        self.assertEqual(HistoryRecord.objects.count(), before)

    def test_changed_text_creates_history_record(self):
        make_translation(self.token, self.lang, 'Old')
        before = HistoryRecord.objects.count()
        self._post({'project_id': self.project.pk, 'code': 'EN', 'token': 'greeting', 'translation': 'New'})
        self.assertEqual(HistoryRecord.objects.count(), before + 1)

    def test_missing_token_returns_404(self):
        resp = self._post({'project_id': self.project.pk, 'code': 'EN', 'token': 'no_such_token', 'translation': 'x'})
        self.assertEqual(resp.status_code, 404)

    def test_unknown_language_returns_400(self):
        resp = self._post({'project_id': self.project.pk, 'code': 'ZZ', 'token': 'greeting', 'translation': 'x'})
        self.assertEqual(resp.status_code, 400)

    def test_unauthenticated_returns_401(self):
        from rest_framework.test import APIClient
        resp = APIClient().post('/api/translation', {}, format='json')
        self.assertEqual(resp.status_code, 401)


class TranslationStatusAPITestCase(TestCase):

    def setUp(self):
        self.user = make_user('owner')
        self.project = make_project('P', owner=self.user)
        self.lang = make_language(self.project, 'EN')
        self.token = make_token(self.project, 'key')
        make_translation(self.token, self.lang, 'Hi')
        self.client = authed_client(self.user)

    def _put(self, data):
        return self.client.put('/api/translation/status', data, format='json')

    def test_valid_status_updates(self):
        resp = self._put({'project_id': self.project.pk, 'code': 'EN', 'token': 'key', 'status': 'approved'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Translation.objects.get(token=self.token, language=self.lang).status, 'approved')

    def test_status_new_rejected(self):
        resp = self._put({'project_id': self.project.pk, 'code': 'EN', 'token': 'key', 'status': 'new'})
        self.assertEqual(resp.status_code, 400)

    def test_invalid_status_string_rejected(self):
        resp = self._put({'project_id': self.project.pk, 'code': 'EN', 'token': 'key', 'status': 'garbage'})
        self.assertEqual(resp.status_code, 400)


class PluralTranslationAPITestCase(TestCase):

    def setUp(self):
        self.user = make_user('owner')
        self.project = make_project('P', owner=self.user)
        self.lang = make_language(self.project, 'EN')
        self.token = make_token(self.project, 'item')
        self.client = authed_client(self.user)

    def _put(self, data):
        return self.client.put('/api/plural', data, format='json')

    def test_creates_plural_forms(self):
        resp = self._put({'project_id': self.project.pk, 'code': 'EN', 'token': 'item',
                          'plural_forms': {'one': 'one item', 'other': 'many items'}})
        self.assertEqual(resp.status_code, 200)
        tr = Translation.objects.get(token=self.token, language=self.lang)
        self.assertEqual(tr.status, Translation.Status.in_review)
        self.assertEqual(tr.plural_forms.count(), 2)

    def test_plural_forms_not_dict_rejected(self):
        resp = self._put({'project_id': self.project.pk, 'code': 'EN', 'token': 'item',
                          'plural_forms': ['one', 'other']})
        self.assertEqual(resp.status_code, 400)

    def test_unknown_form_key_rejected(self):
        resp = self._put({'project_id': self.project.pk, 'code': 'EN', 'token': 'item',
                          'plural_forms': {'singular': 'bad key'}})
        self.assertEqual(resp.status_code, 400)

    def test_missing_token_returns_404(self):
        resp = self._put({'project_id': self.project.pk, 'code': 'EN', 'token': 'no_such',
                          'plural_forms': {'one': 'x'}})
        self.assertEqual(resp.status_code, 404)

    def test_missing_fields_returns_400(self):
        resp = self._put({'plural_forms': {'one': 'x'}})
        self.assertEqual(resp.status_code, 400)
