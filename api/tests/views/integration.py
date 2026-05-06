import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from api.crypto import encrypt
from api.models.project import ProjectAIProvider, ProjectRole, TranslationIntegration
from api.tests.helpers import add_role, authed_client, make_project, make_user

OPENAI_RESPONSE = json.dumps({
    'choices': [{'message': {'content': 'Bonjour'}}]
}).encode()

ANTHROPIC_RESPONSE = json.dumps({
    'content': [{'text': 'Bonjour'}]
}).encode()


def _mock_urlopen(response_body: bytes):
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read.return_value = response_body
    return MagicMock(return_value=mock_resp)


def _make_ai_provider(project, provider_type='openai'):
    return ProjectAIProvider.objects.create(
        project=project,
        provider_type=provider_type,
        model_name='gpt-4o-mini',
        endpoint_url='',
        api_key=encrypt('sk-test'),
    )


class CreateConnectedAIIntegrationTestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)

    def test_create_connected_ai_without_api_key(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/integration', {
            'provider': 'ai',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['enabled'])
        self.assertEqual(data['provider'], 'ai')
        self.assertEqual(self.project.integration.provider, 'ai')
        self.assertIsNone(self.project.integration.api_key)

    def test_provider_label_is_use_connected_ai(self):
        self.client.post(f'/api/project/{self.project.pk}/integration', {
            'provider': 'ai',
        }, format='json')
        resp = self.client.get(f'/api/project/{self.project.pk}/integration')
        self.assertEqual(resp.json()['provider_label'], 'Use Connected AI')

    def test_non_admin_cannot_configure(self):
        member = make_user('member')
        add_role(member, self.project, ProjectRole.Role.translator)
        client = authed_client(member)
        resp = client.post(f'/api/project/{self.project.pk}/integration', {
            'provider': 'ai',
        }, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_deepl_still_requires_api_key(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/integration', {
            'provider': 'deepl',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('api_key', resp.json()['error'])


class GetConnectedAIIntegrationTestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)
        TranslationIntegration.objects.create(
            project=self.project,
            provider='ai',
            api_key=None,
        )

    def test_get_does_not_return_extra_fields(self):
        resp = self.client.get(f'/api/project/{self.project.pk}/integration')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['enabled'])
        self.assertEqual(data['provider'], 'ai')
        self.assertNotIn('endpoint_url', data)
        self.assertNotIn('payload_template', data)
        self.assertNotIn('response_path', data)

    def test_providers_list_contains_connected_ai(self):
        resp = self.client.get(f'/api/project/{self.project.pk}/integration')
        providers = {p['value']: p['label'] for p in resp.json()['providers']}
        self.assertIn('ai', providers)
        self.assertEqual(providers['ai'], 'Use Connected AI')
        self.assertNotIn('Generic AI', providers.values())


class VerifyConnectedAIIntegrationTestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)
        TranslationIntegration.objects.create(
            project=self.project,
            provider='ai',
            api_key=None,
        )
        _make_ai_provider(self.project)

    @patch('urllib.request.urlopen', _mock_urlopen(OPENAI_RESPONSE))
    def test_verify_uses_connected_ai(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/integration/verify')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['ok'])

    def test_verify_fails_without_ai_provider(self):
        ProjectAIProvider.objects.filter(project=self.project).delete()
        resp = self.client.post(f'/api/project/{self.project.pk}/integration/verify')
        self.assertEqual(resp.status_code, 502)
        self.assertIn('error', resp.json())

    @patch('urllib.request.urlopen')
    def test_verify_http_error(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='', code=401, msg='Unauthorized', hdrs=None, fp=None
        )
        resp = self.client.post(f'/api/project/{self.project.pk}/integration/verify')
        self.assertEqual(resp.status_code, 502)
        self.assertIn('error', resp.json())


class MachineTranslateConnectedAITestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)
        TranslationIntegration.objects.create(
            project=self.project,
            provider='ai',
            api_key=None,
        )
        _make_ai_provider(self.project, provider_type='openai')

    @patch('urllib.request.urlopen', _mock_urlopen(OPENAI_RESPONSE))
    def test_translate_via_openai_provider(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/machine-translate', {
            'text': 'Hello',
            'target_language': 'FR',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['translation'], 'Bonjour')

    @patch('urllib.request.urlopen', _mock_urlopen(ANTHROPIC_RESPONSE))
    def test_translate_via_anthropic_provider(self):
        ProjectAIProvider.objects.filter(project=self.project).delete()
        _make_ai_provider(self.project, provider_type='anthropic')
        resp = self.client.post(f'/api/project/{self.project.pk}/machine-translate', {
            'text': 'Hello',
            'target_language': 'FR',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['translation'], 'Bonjour')

    def test_translate_fails_without_ai_provider(self):
        ProjectAIProvider.objects.filter(project=self.project).delete()
        resp = self.client.post(f'/api/project/{self.project.pk}/machine-translate', {
            'text': 'Hello',
            'target_language': 'FR',
        }, format='json')
        self.assertEqual(resp.status_code, 502)


class ConnectedAISSRFTestCase(TestCase):
    """SSRF guard: connected AI provider must reject private endpoint URLs."""

    def setUp(self):
        self.owner = make_user('ssrf_owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)
        TranslationIntegration.objects.create(
            project=self.project,
            provider='ai',
            api_key=None,
        )
        ProjectAIProvider.objects.create(
            project=self.project,
            provider_type='openai',
            model_name='gpt-4o-mini',
            endpoint_url='https://10.0.0.1/v1/chat/completions',
            api_key=encrypt('sk-test'),
        )

    def _mock_addr(self, ip):
        import socket
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, '', (ip, 0))]

    def test_connected_ai_blocked_for_private_url(self):
        with patch('socket.getaddrinfo', return_value=self._mock_addr('10.0.0.1')), \
             patch('api.translation_providers.connected_ai.urllib.request.urlopen') as mock_urlopen:
            resp = self.client.post(
                f'/api/project/{self.project.pk}/machine-translate',
                {'text': 'Hello', 'target_language': 'FR'},
                format='json',
            )
        mock_urlopen.assert_not_called()
        self.assertEqual(resp.status_code, 502)


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
