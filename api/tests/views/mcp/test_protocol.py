import json

from django.test import TestCase, Client

from api.tests.helpers import make_access_token, make_language, make_project, make_user
from .helpers import mcp_call


class McpProtocolTestCase(TestCase):

    def setUp(self):
        self.user = make_user('dev')
        self.project = make_project('MyApp', owner=self.user)
        make_language(self.project, 'EN')
        self.access = make_access_token(self.project, self.user)
        self.client = Client()

    def _post(self, body, token=None):
        return self.client.post(
            '/api/mcp', json.dumps(body),
            content_type='application/json',
            HTTP_ACCESS_TOKEN=(token or self.access.token),
        )

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
        self.assertEqual(resp.json()['name'], 'strings-repository')

    def test_initialize(self):
        resp = self._post({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                'protocolVersion': '2024-11-05',
                'capabilities': {},
                'clientInfo': {'name': 'test', 'version': '0'},
            },
        })
        data = resp.json()
        self.assertEqual(data['id'], 1)
        self.assertIn('protocolVersion', data['result'])
        self.assertIn('tools', data['result']['capabilities'])

    def test_tools_list_contains_all_tools(self):
        resp = self._post({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = {t['name'] for t in resp.json()['result']['tools']}
        for expected in (
            'get_project', 'get_languages',
            'list_tokens', 'get_token', 'create_token', 'set_translation', 'batch_create_tokens',
            'search_similar_tokens', 'suggest_token_key', 'get_token_naming_patterns',
            'check_glossary', 'suggest_translation', 'verify_string',
        ):
            self.assertIn(expected, names)

    def test_notification_returns_empty_200(self):
        resp = self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b'{}')

    def test_unknown_method_returns_error(self):
        resp = self._post({"jsonrpc": "2.0", "id": 1, "method": "unknown/method"})
        data = resp.json()
        self.assertIn('error', data)
        self.assertEqual(data['error']['code'], -32601)

    def test_invalid_json_returns_parse_error(self):
        resp = self.client.post(
            '/api/mcp', 'not json',
            content_type='application/json',
            HTTP_ACCESS_TOKEN=self.access.token,
        )
        self.assertEqual(resp.json()['error']['code'], -32700)

    def test_unknown_tool_returns_error(self):
        resp = mcp_call(self.client, self.access, 'no_such_tool', {})
        data = resp.json()
        self.assertIn('error', data)
        self.assertEqual(data['error']['code'], -32601)
