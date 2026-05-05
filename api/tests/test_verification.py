from datetime import datetime, timezone
from unittest.mock import patch

from django.test import TestCase

from api.crypto import encrypt
from api.models.project import ProjectAIProvider, ProjectRole
from api.models.string_token import StringToken
from api.models.verification import VerificationReport
from api.tests.helpers import (
    add_role, authed_client, make_language, make_project, make_token, make_translation, make_user,
)


def _make_ai_provider(project):
    return ProjectAIProvider.objects.create(
        project=project,
        provider_type='openai',
        model_name='gpt-4o-mini',
        endpoint_url='',
        api_key=encrypt('sk-test'),
    )


def _make_complete_report(project, user, mode='source_quality', target_language=''):
    return VerificationReport.objects.create(
        project=project,
        created_by=user,
        mode=mode,
        target_language=target_language,
        checks=['spelling_grammar'],
        status=VerificationReport.Status.complete,
        result={
            'results': [],
            'summary': {'ok': 1, 'warning': 0, 'error': 0, 'total': 1},
        },
        completed_at=datetime.now(timezone.utc),
    )


class VerificationListTestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)

    def test_get_returns_404_when_no_ai_provider(self):
        resp = self.client.get(f'/api/project/{self.project.pk}/verify')
        self.assertEqual(resp.status_code, 404)

    def test_get_returns_empty_list_when_provider_exists(self):
        _make_ai_provider(self.project)
        resp = self.client.get(f'/api/project/{self.project.pk}/verify')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])


class VerificationCountTestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)
        self.lang = make_language(self.project, 'EN')
        make_token(self.project, 'key1')
        make_token(self.project, 'key2')

    def test_count_mode1_returns_active_token_count(self):
        resp = self.client.get(
            f'/api/project/{self.project.pk}/verify/count?mode=source_quality'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['count'], 2)

    def test_count_by_translator_returns_403(self):
        translator = make_user('translator')
        add_role(translator, self.project, ProjectRole.Role.translator)
        client = authed_client(translator)
        resp = client.get(f'/api/project/{self.project.pk}/verify/count?mode=source_quality')
        self.assertEqual(resp.status_code, 403)


class VerificationCreateTestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)
        _make_ai_provider(self.project)
        make_language(self.project, 'EN')
        make_token(self.project, 'key1')

    def test_post_by_translator_returns_403(self):
        translator = make_user('translator')
        add_role(translator, self.project, ProjectRole.Role.translator)
        client = authed_client(translator)
        with patch('api.views.verification.async_task'):
            resp = client.post(f'/api/project/{self.project.pk}/verify', {
                'mode': 'source_quality',
                'checks': ['spelling_grammar'],
            }, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_post_with_missing_checks_returns_400(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/verify', {
            'mode': 'source_quality',
            'checks': [],
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_post_mode2_without_target_language_returns_400(self):
        resp = self.client.post(f'/api/project/{self.project.pk}/verify', {
            'mode': 'translation_accuracy',
            'target_language': '',
            'checks': ['semantic_accuracy'],
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_post_creates_pending_report_and_enqueues_task(self):
        with patch('api.views.verification.async_task') as mock_task:
            resp = self.client.post(f'/api/project/{self.project.pk}/verify', {
                'mode': 'source_quality',
                'checks': ['spelling_grammar'],
            }, format='json')
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data['status'], 'pending')
        mock_task.assert_called_once()

    def test_post_duplicate_active_returns_409(self):
        with patch('api.views.verification.async_task'):
            self.client.post(f'/api/project/{self.project.pk}/verify', {
                'mode': 'source_quality',
                'checks': ['spelling_grammar'],
            }, format='json')

        with patch('api.views.verification.async_task'):
            resp = self.client.post(f'/api/project/{self.project.pk}/verify', {
                'mode': 'source_quality',
                'checks': ['spelling_grammar'],
            }, format='json')
        self.assertEqual(resp.status_code, 409)


class VerificationDetailTestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)
        _make_ai_provider(self.project)
        self.report = _make_complete_report(self.project, self.owner)

    def test_get_report_by_any_member(self):
        translator = make_user('translator')
        add_role(translator, self.project, ProjectRole.Role.translator)
        client = authed_client(translator)
        resp = client.get(f'/api/project/{self.project.pk}/verify/{self.report.pk}')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['id'], self.report.pk)

    def test_delete_by_owner_returns_204(self):
        resp = self.client.delete(f'/api/project/{self.project.pk}/verify/{self.report.pk}')
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(VerificationReport.objects.filter(pk=self.report.pk).exists())

    def test_delete_by_editor_returns_404(self):
        editor = make_user('editor')
        add_role(editor, self.project, ProjectRole.Role.editor)
        client = authed_client(editor)
        resp = client.delete(f'/api/project/{self.project.pk}/verify/{self.report.pk}')
        # View returns 404 when permission denied (project not found for role)
        self.assertEqual(resp.status_code, 404)


class VerificationApplyTestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.client = authed_client(self.owner)
        _make_ai_provider(self.project)
        self.lang = make_language(self.project, 'EN')
        self.lang.is_default = True
        self.lang.save()
        self.token = make_token(self.project, 'key1')
        make_translation(self.token, self.lang, 'Hello')
        self.report = _make_complete_report(self.project, self.owner)

    def test_apply_marks_report_readonly(self):
        resp = self.client.post(
            f'/api/project/{self.project.pk}/verify/{self.report.pk}/apply',
            {'suggestions': [{'token_id': self.token.pk, 'plural_form': None, 'text': 'Hi'}]},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.report.refresh_from_db()
        self.assertTrue(self.report.is_readonly)

    def test_apply_by_translator_returns_403(self):
        translator = make_user('translator')
        add_role(translator, self.project, ProjectRole.Role.translator)
        client = authed_client(translator)
        resp = client.post(
            f'/api/project/{self.project.pk}/verify/{self.report.pk}/apply',
            {'suggestions': [{'token_id': self.token.pk, 'plural_form': None, 'text': 'Hi'}]},
            format='json',
        )
        self.assertEqual(resp.status_code, 403)


class VerificationCommentTestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        _make_ai_provider(self.project)
        self.report = _make_complete_report(self.project, self.owner)

    def test_translator_can_add_comment(self):
        translator = make_user('translator')
        add_role(translator, self.project, ProjectRole.Role.translator)
        client = authed_client(translator)
        resp = client.post(
            f'/api/project/{self.project.pk}/verify/{self.report.pk}/comments',
            {'token_id': 1, 'token_key': 'key1', 'plural_form': '', 'text': 'Looks wrong'},
            format='json',
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data['text'], 'Looks wrong')

    def test_comment_without_text_returns_400(self):
        client = authed_client(self.owner)
        resp = client.post(
            f'/api/project/{self.project.pk}/verify/{self.report.pk}/comments',
            {'token_id': 1, 'token_key': 'key1', 'text': ''},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)


class VerificationCapTestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)
        self.project.verification_cap = 10
        self.project.save()
        _make_ai_provider(self.project)

    def test_cap_enforcement_deletes_oldest_when_exceeded(self):
        for i in range(11):
            VerificationReport.objects.create(
                project=self.project,
                created_by=self.owner,
                mode='source_quality',
                checks=['spelling_grammar'],
                status=VerificationReport.Status.complete,
            )
        from api.tasks import _enforce_cap
        _enforce_cap(self.project)
        count = VerificationReport.objects.filter(project=self.project).count()
        self.assertEqual(count, 10)


class ValidateDescriptionTestCase(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)

    def test_patch_description_by_translator_returns_400(self):
        translator = make_user('translator')
        add_role(translator, self.project, ProjectRole.Role.translator)
        client = authed_client(translator)
        resp = client.patch(
            f'/api/project/{self.project.pk}',
            {'description': 'new desc'},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_patch_description_by_admin_succeeds(self):
        admin = make_user('admin_user')
        add_role(admin, self.project, ProjectRole.Role.admin)
        client = authed_client(admin)
        resp = client.patch(
            f'/api/project/{self.project.pk}',
            {'description': 'new desc'},
            format='json',
        )
        self.assertIn(resp.status_code, [200, 201])
