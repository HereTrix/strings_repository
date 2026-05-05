from unittest.mock import patch

from django.test import TestCase

from api.crypto import encrypt
from api.models.project import ProjectAIProvider, ProjectRole
from api.tests.helpers import add_role, authed_client, make_project, make_user


def _make_ai_provider(project, provider_type='openai', model_name='gpt-4o-mini', endpoint_url=''):
    return ProjectAIProvider.objects.create(
        project=project,
        provider_type=provider_type,
        model_name=model_name,
        endpoint_url=endpoint_url,
        api_key=encrypt('sk-test'),
    )


class AIProviderGetTestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)

    def test_get_returns_disabled_when_no_provider(self):
        resp = self.client.get(f'/api/project/{self.project.pk}/ai-provider')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data['enabled'])
        self.assertIn('providers', data)

    def test_get_returns_provider_when_configured(self):
        _make_ai_provider(self.project)
        resp = self.client.get(f'/api/project/{self.project.pk}/ai-provider')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['enabled'])
        self.assertEqual(data['provider_type'], 'openai')
        self.assertEqual(data['model_name'], 'gpt-4o-mini')
        self.assertNotIn('api_key', data)

    def test_get_returns_404_for_non_member(self):
        outsider = make_user('outsider')
        client = authed_client(outsider)
        resp = client.get(f'/api/project/{self.project.pk}/ai-provider')
        self.assertEqual(resp.status_code, 404)


class AIProviderCreateTestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)

    def test_post_by_owner_creates_provider(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/ai-provider', {
            'provider_type': 'openai',
            'api_key': 'sk-test',
            'model_name': 'gpt-4o-mini',
            'endpoint_url': '',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['enabled'])
        self.assertEqual(data['provider_type'], 'openai')
        self.assertNotIn('api_key', data)

    def test_post_by_translator_returns_403(self):
        translator = make_user('translator')
        add_role(translator, self.project, ProjectRole.Role.translator)
        client = authed_client(translator)
        resp = client.post(f'/api/project/{self.project.pk}/ai-provider', {
            'provider_type': 'openai',
            'api_key': 'sk-test',
            'model_name': 'gpt-4o-mini',
        }, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_post_with_invalid_provider_type_returns_400(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/ai-provider', {
            'provider_type': 'invalid_type',
            'api_key': 'sk-test',
            'model_name': 'gpt-4o-mini',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_post_with_missing_model_name_returns_400(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/ai-provider', {
            'provider_type': 'openai',
            'api_key': 'sk-test',
            'model_name': '',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_post_without_api_key_on_new_provider_returns_400(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/ai-provider', {
            'provider_type': 'openai',
            'api_key': '',
            'model_name': 'gpt-4o-mini',
        }, format='json')
        self.assertEqual(resp.status_code, 400)


class AIProviderDeleteTestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)
        _make_ai_provider(self.project)

    def test_delete_by_owner_removes_provider(self):
        resp = self.client.delete(f'/api/project/{self.project.pk}/ai-provider')
        self.assertEqual(resp.status_code, 204)
        get_resp = self.client.get(f'/api/project/{self.project.pk}/ai-provider')
        self.assertFalse(get_resp.json()['enabled'])

    def test_delete_by_editor_returns_403(self):
        editor = make_user('editor')
        add_role(editor, self.project, ProjectRole.Role.editor)
        client = authed_client(editor)
        resp = client.delete(f'/api/project/{self.project.pk}/ai-provider')
        self.assertEqual(resp.status_code, 403)
