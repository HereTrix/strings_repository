import json

from django.test import TestCase, Client

from api.models.string_token import StringToken
from api.models.translations import Translation
from api.tests.helpers import (
    make_access_token, make_language, make_project, make_token,
    make_translation, make_user,
)


class McpPhase2TestCase(TestCase):

    def setUp(self):
        self.user = make_user('dev2')
        self.project = make_project('Phase2App', owner=self.user)
        self.lang_en = make_language(self.project, 'EN')
        self.access = make_access_token(self.project, self.user)
        self.client = Client()

        self.token_a = make_token(self.project, 'onboarding.title')
        self.token_b = make_token(self.project, 'onboarding.subtitle')
        self.token_c = make_token(self.project, 'settings.profile')
        make_translation(self.token_a, self.lang_en, 'Welcome to the app')
        make_translation(self.token_b, self.lang_en, 'Get started here')
        make_translation(self.token_c, self.lang_en, 'Edit your profile')

    def _mcp(self, method, params=None, id_=1):
        body = {"jsonrpc": "2.0", "id": id_, "method": method}
        if params is not None:
            body["params"] = params
        return self.client.post(
            '/api/mcp',
            json.dumps(body),
            content_type='application/json',
            HTTP_ACCESS_TOKEN=self.access.token,
        )

    def _result(self, resp):
        return json.loads(resp.content)

    def _call(self, name, arguments):
        resp = self._mcp('tools/call', {'name': name, 'arguments': arguments})
        data = self._result(resp)
        self.assertNotIn('error', data, msg=f"Tool {name} returned error: {data.get('error')}")
        return json.loads(data['result']['content'][0]['text'])

    # ── search_similar_tokens ─────────────────────────────────────────────────

    def test_search_finds_by_translation_text(self):
        result = self._call('search_similar_tokens', {'text': 'Welcome'})
        tokens = [r['token'] for r in result['results']]
        self.assertIn('onboarding.title', tokens)

    def test_search_finds_by_key_name(self):
        result = self._call('search_similar_tokens', {'text': 'settings'})
        tokens = [r['token'] for r in result['results']]
        self.assertIn('settings.profile', tokens)

    def test_search_respects_limit(self):
        result = self._call('search_similar_tokens', {'text': 'onboarding', 'limit': 1})
        self.assertLessEqual(len(result['results']), 1)

    def test_search_returns_translations(self):
        result = self._call('search_similar_tokens', {'text': 'Welcome'})
        first = result['results'][0]
        self.assertIn('translations', first)
        langs = [t['language'] for t in first['translations']]
        self.assertIn('EN', langs)

    # ── suggest_token_key ─────────────────────────────────────────────────────

    def test_suggest_basic(self):
        result = self._call('suggest_token_key', {'source_text': 'Sign in to your account'})
        self.assertEqual(result['suggested_key'], 'sign_in_to_your_account')

    def test_suggest_strips_punctuation(self):
        result = self._call('suggest_token_key', {'source_text': "Don't miss out!"})
        key = result['suggested_key']
        self.assertNotIn("'", key)
        self.assertNotIn('!', key)

    def test_suggest_avoids_collision(self):
        result = self._call('suggest_token_key', {
            'source_text': 'Hello world',
            'existing_tokens': ['hello_world'],
        })
        self.assertEqual(result['suggested_key'], 'hello_world_2')

    def test_suggest_increments_collision_counter(self):
        result = self._call('suggest_token_key', {
            'source_text': 'Hello world',
            'existing_tokens': ['hello_world', 'hello_world_2'],
        })
        self.assertEqual(result['suggested_key'], 'hello_world_3')

    def test_suggest_truncates_to_five_words(self):
        result = self._call('suggest_token_key', {'source_text': 'one two three four five six seven'})
        parts = result['suggested_key'].split('_')
        self.assertLessEqual(len(parts), 5)

    # ── get_token_naming_patterns ─────────────────────────────────────────────

    def test_naming_patterns_detects_dot_separator(self):
        result = self._call('get_token_naming_patterns', {})
        self.assertEqual(result['separator'], 'dot')

    def test_naming_patterns_common_prefixes(self):
        result = self._call('get_token_naming_patterns', {'sample_size': 10})
        self.assertIn('onboarding', result['common_prefixes'])

    def test_naming_patterns_returns_examples(self):
        result = self._call('get_token_naming_patterns', {})
        self.assertGreater(len(result['examples']), 0)

    def test_naming_patterns_underscore_detection(self):
        project2 = make_project('UnderscoreApp', owner=self.user)
        lang = make_language(project2, 'EN')
        for key in ('home_title', 'home_subtitle', 'profile_name'):
            make_token(project2, key)
        access2 = make_access_token(project2, self.user)

        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                           "params": {"name": "get_token_naming_patterns", "arguments": {}}})
        resp = self.client.post('/api/mcp', body, content_type='application/json',
                                HTTP_ACCESS_TOKEN=access2.token)
        result = json.loads(json.loads(resp.content)['result']['content'][0]['text'])
        self.assertEqual(result['separator'], 'underscore')

    # ── batch_create_tokens ───────────────────────────────────────────────────

    def test_batch_creates_tokens_with_translations(self):
        entries = [
            {'token_key': 'batch.a', 'language_code': 'EN', 'text': 'Batch A'},
            {'token_key': 'batch.b', 'language_code': 'EN', 'text': 'Batch B'},
        ]
        result = self._call('batch_create_tokens', {'entries': entries})
        self.assertEqual(sorted(result['created']), ['batch.a', 'batch.b'])
        self.assertEqual(result['skipped'], [])
        self.assertEqual(result['failed'], [])

        self.assertTrue(StringToken.objects.filter(token='batch.a', project=self.project).exists())
        tr = Translation.objects.get(
            token__token='batch.a', token__project=self.project, language=self.lang_en
        )
        self.assertEqual(tr.translation, 'Batch A')

    def test_batch_skips_duplicates(self):
        entries = [
            {'token_key': 'onboarding.title'},
            {'token_key': 'batch.new'},
        ]
        result = self._call('batch_create_tokens', {'entries': entries})
        self.assertIn('onboarding.title', result['skipped'])
        self.assertIn('batch.new', result['created'])

    def test_batch_reports_partial_failure(self):
        entries = [
            {'token_key': 'batch.ok'},
            {'token_key': ''},   # invalid — empty key
        ]
        result = self._call('batch_create_tokens', {'entries': entries})
        self.assertIn('batch.ok', result['created'])
        self.assertEqual(len(result['failed']), 1)

    def test_batch_create_without_translation(self):
        entries = [{'token_key': 'key.no.translation'}]
        result = self._call('batch_create_tokens', {'entries': entries})
        self.assertIn('key.no.translation', result['created'])
        self.assertTrue(StringToken.objects.filter(token='key.no.translation').exists())
