from django.test import TestCase, Client

from api.models.project import ProjectAccessToken
from api.models.string_token import StringToken
from api.models.translations import Translation
from api.tests.helpers import (
    make_access_token, make_language, make_project, make_token,
    make_translation, make_user,
)
from .helpers import get_error, get_result, mcp_call


class TokenCrudTestCase(TestCase):

    def setUp(self):
        self.user = make_user('dev')
        self.project = make_project('MyApp', owner=self.user)
        self.lang_en = make_language(self.project, 'EN')
        self.lang_fr = make_language(self.project, 'FR')
        self.token = make_token(self.project, 'greeting', comment='Hello key')
        make_translation(self.token, self.lang_en, 'Hello')
        make_translation(self.token, self.lang_fr, 'Bonjour')
        self.access = make_access_token(self.project, self.user)
        self.read_access = make_access_token(
            self.project, self.user,
            permission=ProjectAccessToken.AccessTokenPermissions.read,
        )
        self.client = Client()

    def _call(self, tool_name, arguments, token=None):
        return mcp_call(self.client, token or self.access, tool_name, arguments)

    # ── list_tokens ───────────────────────────────────────────────────────────

    def test_list_tokens_returns_all(self):
        make_token(self.project, 'farewell')
        result = get_result(self._call('list_tokens', {}))
        self.assertEqual(result['count'], 2)
        self.assertEqual(len(result['results']), 2)

    def test_list_tokens_search_by_key_name(self):
        make_token(self.project, 'farewell')
        result = get_result(self._call('list_tokens', {'search': 'fare'}))
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['results'][0]['token'], 'farewell')

    def test_list_tokens_search_by_translation_text(self):
        result = get_result(self._call('list_tokens', {'search': 'Bonjour'}))
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['results'][0]['token'], 'greeting')

    def test_list_tokens_pagination(self):
        for i in range(5):
            make_token(self.project, f'key_{i}')
        result = get_result(self._call('list_tokens', {'limit': 3, 'offset': 0}))
        self.assertEqual(result['count'], 6)
        self.assertEqual(len(result['results']), 3)

    # ── get_token ─────────────────────────────────────────────────────────────

    def test_get_token_returns_translations(self):
        result = get_result(self._call('get_token', {'token_key': 'greeting'}))
        self.assertEqual(result['token'], 'greeting')
        self.assertEqual(result['comment'], 'Hello key')
        langs = {t['language'] for t in result['translations']}
        self.assertEqual(langs, {'EN', 'FR'})

    def test_get_token_not_found_returns_error(self):
        resp = self._call('get_token', {'token_key': 'no_such'})
        self.assertIn('error', resp.json())

    # ── create_token ──────────────────────────────────────────────────────────

    def test_create_token_succeeds(self):
        result = get_result(self._call('create_token', {
            'token_key': 'new.key', 'comment': 'A new key', 'tags': ['ui'],
        }))
        self.assertEqual(result['token'], 'new.key')
        self.assertTrue(StringToken.objects.filter(token='new.key', project=self.project).exists())

    def test_create_token_duplicate_returns_error(self):
        resp = self._call('create_token', {'token_key': 'greeting'})
        self.assertIn('error', resp.json())

    def test_create_token_read_only_returns_error(self):
        resp = self._call('create_token', {'token_key': 'x'}, token=self.read_access)
        self.assertIn('error', resp.json())

    # ── set_translation ───────────────────────────────────────────────────────

    def test_set_translation_creates_new(self):
        new_token = make_token(self.project, 'new_key')
        result = get_result(self._call('set_translation', {
            'token_key': 'new_key', 'language_code': 'EN', 'text': 'Hello world',
        }))
        self.assertEqual(result['text'], 'Hello world')
        self.assertTrue(Translation.objects.filter(token=new_token, language=self.lang_en).exists())

    def test_set_translation_updates_existing(self):
        resp = self._call('set_translation', {
            'token_key': 'greeting', 'language_code': 'EN', 'text': 'Hi',
        })
        self.assertNotIn('error', resp.json())
        tr = Translation.objects.get(token=self.token, language=self.lang_en)
        self.assertEqual(tr.translation, 'Hi')

    def test_set_translation_missing_token_returns_error(self):
        resp = self._call('set_translation', {'token_key': 'no_such', 'language_code': 'EN', 'text': 'x'})
        self.assertIn('error', resp.json())

    def test_set_translation_read_only_returns_error(self):
        resp = self._call('set_translation', {
            'token_key': 'greeting', 'language_code': 'EN', 'text': 'x',
        }, token=self.read_access)
        self.assertIn('error', resp.json())


class BatchCreateTokensTestCase(TestCase):

    def setUp(self):
        self.user = make_user('dev2')
        self.project = make_project('BatchApp', owner=self.user)
        self.lang_en = make_language(self.project, 'EN')
        self.access = make_access_token(self.project, self.user)
        self.client = Client()
        self.existing = make_token(self.project, 'existing.key')

    def _call(self, arguments):
        return mcp_call(self.client, self.access, 'batch_create_tokens', arguments)

    def test_batch_creates_tokens_with_translations(self):
        entries = [
            {'token_key': 'batch.a', 'language_code': 'EN', 'text': 'Batch A'},
            {'token_key': 'batch.b', 'language_code': 'EN', 'text': 'Batch B'},
        ]
        result = get_result(self._call({'entries': entries}))
        self.assertEqual(sorted(result['created']), ['batch.a', 'batch.b'])
        self.assertEqual(result['skipped'], [])
        self.assertEqual(result['failed'], [])
        tr = Translation.objects.get(
            token__token='batch.a', token__project=self.project, language=self.lang_en
        )
        self.assertEqual(tr.translation, 'Batch A')

    def test_batch_skips_duplicates(self):
        result = get_result(self._call({'entries': [
            {'token_key': 'existing.key'},
            {'token_key': 'batch.new'},
        ]}))
        self.assertIn('existing.key', result['skipped'])
        self.assertIn('batch.new', result['created'])

    def test_batch_reports_partial_failure(self):
        result = get_result(self._call({'entries': [
            {'token_key': 'batch.ok'},
            {'token_key': ''},
        ]}))
        self.assertIn('batch.ok', result['created'])
        self.assertEqual(len(result['failed']), 1)

    def test_batch_create_without_translation(self):
        result = get_result(self._call({'entries': [{'token_key': 'key.no.translation'}]}))
        self.assertIn('key.no.translation', result['created'])
        self.assertTrue(StringToken.objects.filter(token='key.no.translation').exists())
