from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APITestCase

from api.crypto import encrypt
from api.models.project import ProjectAIProvider, ProjectRole
from api.models.glossary import GlossaryExtractionJob, GlossaryTerm
from api.models.language import Language
from api.tasks import run_glossary_extraction_job
from api.tests.helpers import (
    make_user, make_project, add_role, make_language, make_token,
    make_translation, authed_client, make_extraction_job, make_glossary_term,
)


def make_ai_provider(project):
    return ProjectAIProvider.objects.create(
        project=project,
        provider_type='openai',
        api_key=encrypt('sk-test'),
        endpoint_url='https://api.openai.com/v1/chat/completions',
        model_name='gpt-4o',
    )


class GlossaryExtractionAPITests(APITestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.translator = make_user('translator')
        self.project = make_project(owner=self.owner)
        add_role(self.translator, self.project, ProjectRole.Role.translator)
        self.owner_client = authed_client(self.owner)
        self.translator_client = authed_client(self.translator)

    def test_trigger_requires_ai_provider(self):
        resp = self.owner_client.post(f'/api/project/{self.project.pk}/glossary/extract')
        self.assertEqual(resp.status_code, 400)

    @patch('api.views.glossary.async_task')
    def test_trigger_creates_job(self, mock_async):
        make_ai_provider(self.project)
        resp = self.owner_client.post(f'/api/project/{self.project.pk}/glossary/extract')
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data['status'], 'pending')
        mock_async.assert_called_once_with('api.tasks.run_glossary_extraction_job', data['id'])

    @patch('api.views.glossary.async_task')
    def test_trigger_rejects_duplicate(self, mock_async):
        make_ai_provider(self.project)
        make_extraction_job(self.project, user=self.owner, status='pending')
        resp = self.owner_client.post(f'/api/project/{self.project.pk}/glossary/extract')
        self.assertEqual(resp.status_code, 409)

    def test_get_returns_404_when_no_job(self):
        resp = self.owner_client.get(f'/api/project/{self.project.pk}/glossary/extract')
        self.assertEqual(resp.status_code, 404)

    @patch('api.views.glossary.async_task')
    def test_get_returns_latest_job(self, mock_async):
        make_ai_provider(self.project)
        self.owner_client.post(f'/api/project/{self.project.pk}/glossary/extract')
        resp = self.owner_client.get(f'/api/project/{self.project.pk}/glossary/extract')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('status', resp.json())

    def test_trigger_requires_admin(self):
        make_ai_provider(self.project)
        resp = self.translator_client.post(f'/api/project/{self.project.pk}/glossary/extract')
        self.assertEqual(resp.status_code, 403)


class GlossarySuggestionsAPITests(APITestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.translator = make_user('translator')
        self.project = make_project(owner=self.owner)
        add_role(self.translator, self.project, ProjectRole.Role.translator)
        make_language(self.project, 'DE')
        self.owner_client = authed_client(self.owner)
        self.translator_client = authed_client(self.translator)

    def test_get_suggestions_empty_when_no_completed_job(self):
        resp = self.owner_client.get(f'/api/project/{self.project.pk}/glossary/suggestions')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_get_suggestions_returns_list(self):
        suggestions = [
            {'term': 'Submit', 'definition': 'To send', 'translations': [], 'status': 'pending'},
        ]
        make_extraction_job(self.project, user=self.owner, status='complete', suggestions=suggestions)
        resp = self.owner_client.get(f'/api/project/{self.project.pk}/glossary/suggestions')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_accept_suggestion_creates_term(self):
        suggestions = [
            {'term': 'Submit', 'definition': 'To send', 'translations': [{'language_code': 'DE', 'preferred_translation': 'Absenden'}], 'status': 'pending'},
        ]
        make_extraction_job(self.project, user=self.owner, status='complete', suggestions=suggestions)
        resp = self.owner_client.patch(
            f'/api/project/{self.project.pk}/glossary/suggestions',
            {'index': 0, 'action': 'accept'},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['suggestion']['status'], 'accepted')
        self.assertTrue(GlossaryTerm.objects.filter(project=self.project, term='Submit').exists())

    def test_accept_with_overrides(self):
        suggestions = [
            {'term': 'Submit', 'definition': 'To send', 'translations': [], 'status': 'pending'},
        ]
        make_extraction_job(self.project, user=self.owner, status='complete', suggestions=suggestions)
        resp = self.owner_client.patch(
            f'/api/project/{self.project.pk}/glossary/suggestions',
            {'index': 0, 'action': 'accept', 'term': 'OverrideTerm', 'translations': []},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(GlossaryTerm.objects.filter(project=self.project, term='OverrideTerm').exists())

    def test_accept_merges_existing_term(self):
        make_glossary_term(self.project, term='Submit', definition='Old def')
        suggestions = [
            {'term': 'Submit', 'definition': 'New def', 'translations': [], 'status': 'pending'},
        ]
        make_extraction_job(self.project, user=self.owner, status='complete', suggestions=suggestions)
        resp = self.owner_client.patch(
            f'/api/project/{self.project.pk}/glossary/suggestions',
            {'index': 0, 'action': 'accept'},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(GlossaryTerm.objects.filter(project=self.project, term='Submit').count(), 1)
        self.assertEqual(GlossaryTerm.objects.get(project=self.project, term='Submit').definition, 'New def')

    def test_reject_suggestion(self):
        suggestions = [
            {'term': 'Submit', 'definition': '', 'translations': [], 'status': 'pending'},
        ]
        make_extraction_job(self.project, user=self.owner, status='complete', suggestions=suggestions)
        resp = self.owner_client.patch(
            f'/api/project/{self.project.pk}/glossary/suggestions',
            {'index': 0, 'action': 'reject'},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['suggestion']['status'], 'rejected')
        self.assertFalse(GlossaryTerm.objects.filter(project=self.project, term='Submit').exists())

    def test_double_action_returns_409(self):
        suggestions = [
            {'term': 'Submit', 'definition': '', 'translations': [], 'status': 'accepted'},
        ]
        make_extraction_job(self.project, user=self.owner, status='complete', suggestions=suggestions)
        resp = self.owner_client.patch(
            f'/api/project/{self.project.pk}/glossary/suggestions',
            {'index': 0, 'action': 'accept'},
            format='json'
        )
        self.assertEqual(resp.status_code, 409)

    def test_requires_admin(self):
        resp = self.translator_client.patch(
            f'/api/project/{self.project.pk}/glossary/suggestions',
            {'index': 0, 'action': 'accept'},
            format='json'
        )
        self.assertEqual(resp.status_code, 403)


class RunGlossaryExtractionJobTests(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)

    def test_task_sets_failed_when_no_ai_provider(self):
        job = make_extraction_job(self.project, user=self.owner, status='pending')
        run_glossary_extraction_job(job.pk)
        job.refresh_from_db()
        self.assertEqual(job.status, 'failed')
        self.assertIn('No AI provider', job.error_message)

    @patch('api.verification_providers.get_verification_provider')
    def test_task_sets_complete_on_success(self, mock_get_provider):
        make_ai_provider(self.project)
        lang = make_language(self.project, 'EN')
        Language.objects.filter(pk=lang.pk).update(is_default=True)
        lang.refresh_from_db()
        token = make_token(self.project, key='greeting')
        make_translation(token, lang, text='Hello')
        mock_provider = MagicMock()
        mock_provider.extract_glossary.return_value = [
            {'term': 'Submit', 'definition': 'To send', 'translations': []},
        ]
        mock_get_provider.return_value = mock_provider
        job = make_extraction_job(self.project, user=self.owner, status='pending')
        run_glossary_extraction_job(job.pk)
        job.refresh_from_db()
        self.assertEqual(job.status, 'complete')
        self.assertEqual(len(job.suggestions), 1)
        self.assertEqual(job.suggestions[0]['status'], 'pending')
        self.assertEqual(job.suggestions[0]['term'], 'Submit')

    @patch('api.verification_providers.get_verification_provider')
    def test_task_sets_failed_on_provider_error(self, mock_get_provider):
        make_ai_provider(self.project)
        lang = make_language(self.project, 'EN')
        Language.objects.filter(pk=lang.pk).update(is_default=True)
        lang.refresh_from_db()
        token = make_token(self.project, key='greeting')
        make_translation(token, lang, text='Hello')
        mock_provider = MagicMock()
        mock_provider.extract_glossary.side_effect = RuntimeError('API error')
        mock_get_provider.return_value = mock_provider
        job = make_extraction_job(self.project, user=self.owner, status='pending')
        run_glossary_extraction_job(job.pk)
        job.refresh_from_db()
        self.assertEqual(job.status, 'failed')
        self.assertIn('API error', job.error_message)

    @patch('api.verification_providers.get_verification_provider')
    def test_task_caps_strings_at_200(self, mock_get_provider):
        make_ai_provider(self.project)
        mock_provider = MagicMock()
        mock_provider.extract_glossary.return_value = []
        mock_get_provider.return_value = mock_provider
        lang = make_language(self.project, 'EN')
        Language.objects.filter(pk=lang.pk).update(is_default=True)
        lang.refresh_from_db()
        for i in range(250):
            token = make_token(self.project, key=f'key_{i}')
            make_translation(token, lang, text=f'String number {i}')
        job = make_extraction_job(self.project, user=self.owner, status='pending')
        run_glossary_extraction_job(job.pk)
        call_args = mock_provider.extract_glossary.call_args
        strings_passed = call_args[0][0]
        self.assertLessEqual(len(strings_passed), 200)
