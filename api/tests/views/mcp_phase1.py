import json

from django.test import TestCase, Client

from api.models.project import ProjectAccessToken
from api.models.string_token import StringToken
from api.models.translations import Translation
from api.tests.helpers import (
    make_access_token, make_language, make_project, make_token,
    make_translation, make_user,
)


class McpPhase1TestCase(TestCase):

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

    def _mcp(self, method, params=None, token=None, id_=1):
        body = {"jsonrpc": "2.0", "id": id_, "method": method}
        if params is not None:
            body["params"] = params
        return self.client.post(
            '/api/mcp',
            json.dumps(body),
            content_type='application/json',
            HTTP_ACCESS_TOKEN=(token or self.access.token),
        )

    def _result(self, resp):
        return json.loads(resp.content)

    # ── auth ──────────────────────────────────────────────────────────────────

    def test_missing_token_returns_403(self):
        resp = self.client.post('/api/mcp', '{}', content_type='application/json')
        self.assertEqual(resp.status_code, 403)

    def test_invalid_token_returns_403(self):
        resp = self.client.post(
            '/api/mcp', '{}',
            content_type='application/json',
            HTTP_ACCESS_TOKEN='badtoken',
        )
        self.assertEqual(resp.status_code, 403)

    # ── protocol ─────────────────────────────────────────────────────────────

    def test_get_returns_server_info(self):
        resp = self.client.get('/api/mcp', HTTP_ACCESS_TOKEN=self.access.token)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data['name'], 'strings-repository')

    def test_initialize(self):
        resp = self._mcp('initialize', params={
            'protocolVersion': '2024-11-05',
            'capabilities': {},
            'clientInfo': {'name': 'test', 'version': '0'},
        })
        data = self._result(resp)
        self.assertEqual(data['id'], 1)
        self.assertIn('protocolVersion', data['result'])
        self.assertIn('tools', data['result']['capabilities'])

    def test_tools_list_contains_phase1_tools(self):
        resp = self._mcp('tools/list')
        tools = self._result(resp)['result']['tools']
        names = {t['name'] for t in tools}
        for expected in ('get_project', 'get_languages', 'list_tokens', 'get_token', 'create_token', 'set_translation'):
            self.assertIn(expected, names)

    def test_notification_returns_empty_200(self):
        body = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
        resp = self.client.post('/api/mcp', body, content_type='application/json',
                                HTTP_ACCESS_TOKEN=self.access.token)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b'{}')

    def test_unknown_method_returns_error(self):
        resp = self._mcp('unknown/method')
        data = self._result(resp)
        self.assertIn('error', data)
        self.assertEqual(data['error']['code'], -32601)

    def test_invalid_json_returns_parse_error(self):
        resp = self.client.post('/api/mcp', 'not json', content_type='application/json',
                                HTTP_ACCESS_TOKEN=self.access.token)
        data = json.loads(resp.content)
        self.assertEqual(data['error']['code'], -32700)

    # ── get_project ───────────────────────────────────────────────────────────

    def test_get_project_returns_project_info(self):
        resp = self._mcp('tools/call', {'name': 'get_project', 'arguments': {}})
        result = json.loads(self._result(resp)['result']['content'][0]['text'])
        self.assertEqual(result['name'], 'MyApp')
        self.assertEqual(result['id'], self.project.id)

    # ── get_languages ─────────────────────────────────────────────────────────

    def test_get_languages_returns_codes(self):
        resp = self._mcp('tools/call', {'name': 'get_languages', 'arguments': {}})
        result = json.loads(self._result(resp)['result']['content'][0]['text'])
        self.assertIn('EN', result['languages'])
        self.assertIn('FR', result['languages'])

    # ── list_tokens ───────────────────────────────────────────────────────────

    def test_list_tokens_returns_all(self):
        make_token(self.project, 'farewell')
        resp = self._mcp('tools/call', {'name': 'list_tokens', 'arguments': {}})
        result = json.loads(self._result(resp)['result']['content'][0]['text'])
        self.assertEqual(result['count'], 2)
        self.assertEqual(len(result['results']), 2)

    def test_list_tokens_search_by_key_name(self):
        make_token(self.project, 'farewell')
        resp = self._mcp('tools/call', {'name': 'list_tokens', 'arguments': {'search': 'fare'}})
        result = json.loads(self._result(resp)['result']['content'][0]['text'])
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['results'][0]['token'], 'farewell')

    def test_list_tokens_search_by_translation_text(self):
        resp = self._mcp('tools/call', {'name': 'list_tokens', 'arguments': {'search': 'Bonjour'}})
        result = json.loads(self._result(resp)['result']['content'][0]['text'])
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['results'][0]['token'], 'greeting')

    def test_list_tokens_pagination(self):
        for i in range(5):
            make_token(self.project, f'key_{i}')
        resp = self._mcp('tools/call', {'name': 'list_tokens', 'arguments': {'limit': 3, 'offset': 0}})
        result = json.loads(self._result(resp)['result']['content'][0]['text'])
        self.assertEqual(result['count'], 6)
        self.assertEqual(len(result['results']), 3)

    # ── get_token ─────────────────────────────────────────────────────────────

    def test_get_token_returns_translations(self):
        resp = self._mcp('tools/call', {'name': 'get_token', 'arguments': {'token_key': 'greeting'}})
        result = json.loads(self._result(resp)['result']['content'][0]['text'])
        self.assertEqual(result['token'], 'greeting')
        self.assertEqual(result['comment'], 'Hello key')
        langs = {t['language'] for t in result['translations']}
        self.assertEqual(langs, {'EN', 'FR'})

    def test_get_token_not_found_returns_error(self):
        resp = self._mcp('tools/call', {'name': 'get_token', 'arguments': {'token_key': 'no_such'}})
        data = self._result(resp)
        self.assertIn('error', data)

    # ── create_token ──────────────────────────────────────────────────────────

    def test_create_token_succeeds(self):
        resp = self._mcp('tools/call', {'name': 'create_token', 'arguments': {
            'token_key': 'new.key', 'comment': 'A new key', 'tags': ['ui'],
        }})
        result = json.loads(self._result(resp)['result']['content'][0]['text'])
        self.assertEqual(result['token'], 'new.key')
        self.assertTrue(StringToken.objects.filter(token='new.key', project=self.project).exists())

    def test_create_token_duplicate_returns_error(self):
        resp = self._mcp('tools/call', {'name': 'create_token', 'arguments': {'token_key': 'greeting'}})
        data = self._result(resp)
        self.assertIn('error', data)
        self.assertIn('already exists', data['error']['message'])

    def test_create_token_read_only_returns_error(self):
        resp = self._mcp('tools/call', {'name': 'create_token', 'arguments': {'token_key': 'x'}},
                         token=self.read_access.token)
        data = self._result(resp)
        self.assertIn('error', data)

    # ── set_translation ───────────────────────────────────────────────────────

    def test_set_translation_creates_new(self):
        new_token = make_token(self.project, 'new_key')
        resp = self._mcp('tools/call', {'name': 'set_translation', 'arguments': {
            'token_key': 'new_key', 'language_code': 'EN', 'text': 'Hello world',
        }})
        result = json.loads(self._result(resp)['result']['content'][0]['text'])
        self.assertEqual(result['text'], 'Hello world')
        self.assertTrue(Translation.objects.filter(token=new_token, language=self.lang_en).exists())

    def test_set_translation_updates_existing(self):
        resp = self._mcp('tools/call', {'name': 'set_translation', 'arguments': {
            'token_key': 'greeting', 'language_code': 'EN', 'text': 'Hi',
        }})
        self.assertNotIn('error', self._result(resp))
        tr = Translation.objects.get(token=self.token, language=self.lang_en)
        self.assertEqual(tr.translation, 'Hi')

    def test_set_translation_missing_token_returns_error(self):
        resp = self._mcp('tools/call', {'name': 'set_translation', 'arguments': {
            'token_key': 'no_such', 'language_code': 'EN', 'text': 'x',
        }})
        data = self._result(resp)
        self.assertIn('error', data)

    def test_set_translation_read_only_returns_error(self):
        resp = self._mcp('tools/call', {'name': 'set_translation', 'arguments': {
            'token_key': 'greeting', 'language_code': 'EN', 'text': 'x',
        }}, token=self.read_access.token)
        self.assertIn('error', self._result(resp))

    def test_unknown_tool_returns_error(self):
        resp = self._mcp('tools/call', {'name': 'no_such_tool', 'arguments': {}})
        data = self._result(resp)
        self.assertIn('error', data)
        self.assertEqual(data['error']['code'], -32601)
