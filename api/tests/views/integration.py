import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from api.crypto import encrypt
from api.models.project import ProjectRole, TranslationIntegration
from api.tests.helpers import add_role, authed_client, make_project, make_user

OPENAI_TEMPLATE = json.dumps({
    'model': 'gpt-4o-mini',
    'messages': [
        {'role': 'system', 'content': 'Translate to {{target_lang}}. Return only the translation.'},
        {'role': 'user', 'content': '{{text}}'},
    ],
})

OPENAI_RESPONSE = json.dumps({
    'choices': [{'message': {'content': 'Bonjour'}}]
}).encode()


def _mock_urlopen(response_body: bytes):
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read.return_value = response_body
    return MagicMock(return_value=mock_resp)


class CreateGenericAIIntegrationTestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)

    def test_create_generic_ai_integration(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/integration', {
            'provider': 'ai',
            'api_key': 'sk-test',
            'endpoint_url': 'https://api.openai.com/v1/chat/completions',
            'payload_template': OPENAI_TEMPLATE,
            'response_path': 'choices.0.message.content',
            'auth_header': 'Authorization',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['enabled'])
        self.assertEqual(data['provider'], 'ai')
        self.assertEqual(data['endpoint_url'], 'https://api.openai.com/v1/chat/completions')
        self.assertEqual(data['response_path'], 'choices.0.message.content')
        integration = self.project.integration
        self.assertEqual(integration.provider, 'ai')
        self.assertEqual(integration.endpoint_url, 'https://api.openai.com/v1/chat/completions')

    def test_create_requires_endpoint_url(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/integration', {
            'provider': 'ai',
            'api_key': 'sk-test',
            'payload_template': OPENAI_TEMPLATE,
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('endpoint_url', resp.json()['error'])

    def test_create_requires_payload_template(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/integration', {
            'provider': 'ai',
            'api_key': 'sk-test',
            'endpoint_url': 'https://api.openai.com/v1/chat/completions',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('payload_template', resp.json()['error'])

    def test_create_invalid_json_template(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/integration', {
            'provider': 'ai',
            'api_key': 'sk-test',
            'endpoint_url': 'https://api.openai.com/v1/chat/completions',
            'payload_template': 'not json {{text}} {{target_lang}}',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('valid JSON', resp.json()['error'])

    def test_create_missing_text_placeholder(self):
        template = json.dumps({'model': 'x', 'messages': [{'role': 'user', 'content': '{{target_lang}}'}]})
        resp = self.client.post(f'/api/project/{self.project.pk}/integration', {
            'provider': 'ai',
            'api_key': 'sk-test',
            'endpoint_url': 'https://api.openai.com/v1/chat/completions',
            'payload_template': template,
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('{{text}}', resp.json()['error'])

    def test_create_missing_target_lang_placeholder(self):
        template = json.dumps({'model': 'x', 'messages': [{'role': 'user', 'content': '{{text}}'}]})
        resp = self.client.post(f'/api/project/{self.project.pk}/integration', {
            'provider': 'ai',
            'api_key': 'sk-test',
            'endpoint_url': 'https://api.openai.com/v1/chat/completions',
            'payload_template': template,
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('{{target_lang}}', resp.json()['error'])

    def test_default_response_path(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/integration', {
            'provider': 'ai',
            'api_key': 'sk-test',
            'endpoint_url': 'https://api.openai.com/v1/chat/completions',
            'payload_template': OPENAI_TEMPLATE,
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.project.integration.response_path, 'choices.0.message.content')

    def test_default_auth_header(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/integration', {
            'provider': 'ai',
            'api_key': 'sk-test',
            'endpoint_url': 'https://api.openai.com/v1/chat/completions',
            'payload_template': OPENAI_TEMPLATE,
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.project.integration.auth_header, 'Authorization')

    def test_non_admin_cannot_configure(self):
        member = make_user('member')
        add_role(member, self.project, ProjectRole.Role.translator)
        client = authed_client(member)
        resp = client.post(f'/api/project/{self.project.pk}/integration', {
            'provider': 'ai',
            'api_key': 'sk-test',
            'endpoint_url': 'https://api.openai.com/v1/chat/completions',
            'payload_template': OPENAI_TEMPLATE,
        }, format='json')
        self.assertEqual(resp.status_code, 403)


class GetGenericAIIntegrationTestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)
        TranslationIntegration.objects.create(
            project=self.project,
            provider='ai',
            api_key=encrypt('sk-test'),
            endpoint_url='https://api.openai.com/v1/chat/completions',
            payload_template=OPENAI_TEMPLATE,
            response_path='choices.0.message.content',
            auth_header='Authorization',
        )

    def test_get_returns_ai_fields(self):
        resp = self.client.get(f'/api/project/{self.project.pk}/integration')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['enabled'])
        self.assertEqual(data['provider'], 'ai')
        self.assertEqual(data['endpoint_url'], 'https://api.openai.com/v1/chat/completions')
        self.assertEqual(data['response_path'], 'choices.0.message.content')
        self.assertEqual(data['auth_header'], 'Authorization')
        self.assertIn('payload_template', data)


class VerifyGenericAIIntegrationTestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)
        TranslationIntegration.objects.create(
            project=self.project,
            provider='ai',
            api_key=encrypt('sk-test'),
            endpoint_url='https://api.openai.com/v1/chat/completions',
            payload_template=OPENAI_TEMPLATE,
            response_path='choices.0.message.content',
            auth_header='Authorization',
        )

    @patch('urllib.request.urlopen', _mock_urlopen(OPENAI_RESPONSE))
    def test_verify_success(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/integration/verify')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['ok'])

    @patch('urllib.request.urlopen')
    def test_verify_http_error(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='', code=401, msg='Unauthorized', hdrs=None, fp=None
        )
        resp = self.client.post(f'/api/project/{self.project.pk}/integration/verify')
        self.assertEqual(resp.status_code, 502)
        self.assertIn('error', resp.json())


class MachineTranslateGenericAITestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)

    def _create_integration(self, response_path='choices.0.message.content', payload_template=None):
        TranslationIntegration.objects.filter(project=self.project).delete()
        TranslationIntegration.objects.create(
            project=self.project,
            provider='ai',
            api_key=encrypt('sk-test'),
            endpoint_url='https://api.openai.com/v1/chat/completions',
            payload_template=payload_template or OPENAI_TEMPLATE,
            response_path=response_path,
            auth_header='Authorization',
        )

    @patch('urllib.request.urlopen', _mock_urlopen(OPENAI_RESPONSE))
    def test_translate_extracts_via_path(self):
        self._create_integration()
        resp = self.client.post(f'/api/project/{self.project.pk}/machine-translate', {
            'text': 'Hello',
            'target_language': 'FR',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['translation'], 'Bonjour')

    @patch('urllib.request.urlopen', _mock_urlopen(OPENAI_RESPONSE))
    def test_translate_bad_response_path(self):
        self._create_integration(response_path='wrong.path.here')
        resp = self.client.post(f'/api/project/{self.project.pk}/machine-translate', {
            'text': 'Hello',
            'target_language': 'FR',
        }, format='json')
        self.assertEqual(resp.status_code, 502)

    @patch('urllib.request.urlopen', _mock_urlopen(OPENAI_RESPONSE))
    def test_custom_auth_header_sent(self):
        TranslationIntegration.objects.filter(project=self.project).delete()
        claude_template = json.dumps({
            'model': 'claude-haiku-4-5-20251001',
            'max_tokens': 1024,
            'system': 'Translate to {{target_lang}}. Return only the translation.',
            'messages': [{'role': 'user', 'content': '{{text}}'}],
        })
        claude_response = json.dumps({'content': [{'text': 'Bonjour'}]}).encode()
        TranslationIntegration.objects.create(
            project=self.project,
            provider='ai',
            api_key=encrypt('sk-ant-test'),
            endpoint_url='https://api.anthropic.com/v1/messages',
            payload_template=claude_template,
            response_path='content.0.text',
            auth_header='x-api-key',
        )
        with patch('urllib.request.urlopen', _mock_urlopen(claude_response)):
            resp = self.client.post(f'/api/project/{self.project.pk}/machine-translate', {
                'text': 'Hello',
                'target_language': 'FR',
            }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['translation'], 'Bonjour')


class ExistingDeepLUnaffectedTestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)
        TranslationIntegration.objects.create(
            project=self.project,
            provider='deepl',
            api_key=encrypt('deepl-key'),
        )

    def test_get_deepl_integration(self):
        resp = self.client.get(f'/api/project/{self.project.pk}/integration')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['provider'], 'deepl')
        self.assertNotIn('endpoint_url', data)

    def test_update_deepl_integration(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/integration', {
            'provider': 'deepl',
            'api_key': 'new-deepl-key',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['provider'], 'deepl')


class GenericAISSRFTestCase(TestCase):
    """VULN-3: SSRF guard in GenericAI provider."""

    def setUp(self):
        import socket
        from api.crypto import encrypt
        from api.models.project import TranslationIntegration
        self.owner = make_user('ssrf_owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)
        self.client.post(f'/api/project/{self.project.pk}/integration', {
            'provider': 'ai',
            'api_key': 'sk-test',
            'endpoint_url': 'https://10.0.0.1/v1/chat',
            'payload_template': OPENAI_TEMPLATE,
            'response_path': 'choices.0.message.content',
        }, format='json')
        from api.models.language import Language
        Language.objects.create(code='EN', project=self.project)
        from api.models.translations import StringToken
        StringToken.objects.create(token='greeting', project=self.project)

    def _mock_addr(self, ip):
        import socket
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, '', (ip, 0))]

    def test_generic_ai_blocked_for_private_url(self):
        with patch('socket.getaddrinfo', return_value=self._mock_addr('10.0.0.1')), \
             patch('api.translation_providers.generic_ai.urllib.request.urlopen') as mock_urlopen:
            resp = self.client.post(
                f'/api/project/{self.project.pk}/machine-translate',
                {'token': 'greeting', 'target_lang': 'FR', 'source_lang': 'EN'},
                format='json',
            )
        mock_urlopen.assert_not_called()
        self.assertIn(resp.status_code, [400, 500])
        body = resp.json()
        self.assertTrue('error' in body or 'detail' in body)
