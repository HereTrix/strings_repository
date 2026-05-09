# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

import socket
from unittest.mock import MagicMock, patch

from django.test import TestCase

from api.crypto import encrypt
from api.models.language import Language
from api.models.project import ProjectAIProvider
from api.models.string_token import StringToken
from api.models.verification import VerificationReport
from api.models.webhook import WebhookDeliveryLog, WebhookEndpoint
from api.tasks import run_glossary_extraction_job, run_verification_job, send_webhook
from api.tests.helpers import (
    make_extraction_job, make_language, make_project, make_token,
    make_translation, make_user,
)

_PUBLIC_ADDR = [(socket.AF_INET, socket.SOCK_STREAM, 0, '', ('8.8.8.8', 0))]


def _make_ai_provider(project):
    return ProjectAIProvider.objects.create(
        project=project,
        provider_type='openai',
        model_name='gpt-4o-mini',
        endpoint_url='',
        api_key=encrypt('sk-test'),
    )


def _set_default_lang(lang):
    Language.objects.filter(pk=lang.pk).update(is_default=True)


def _make_report(project, user, mode='source_quality', target_language='', checks=None):
    return VerificationReport.objects.create(
        project=project,
        created_by=user,
        mode=mode,
        target_language=target_language,
        checks=checks or ['spelling_grammar'],
        status=VerificationReport.Status.pending,
    )


# ---------------------------------------------------------------------------
# api/tasks/glossary.py
# ---------------------------------------------------------------------------

class GlossaryExtractionTaskTests(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)

    def test_returns_early_for_nonexistent_job_id(self):
        run_glossary_extraction_job(999999)  # must not raise

    def test_fails_when_no_strings_in_project(self):
        _make_ai_provider(self.project)
        job = make_extraction_job(self.project, user=self.owner, status='pending')
        run_glossary_extraction_job(job.pk)
        job.refresh_from_db()
        self.assertEqual(job.status, 'failed')
        self.assertIn('No source strings', job.error_message)
        self.assertIsNotNone(job.completed_at)

    @patch('api.verification_providers.get_verification_provider')
    def test_uses_token_keys_when_no_default_language(self, mock_get_provider):
        _make_ai_provider(self.project)
        make_token(self.project, key='submit')
        make_token(self.project, key='cancel')
        mock_provider = MagicMock()
        mock_provider.extract_glossary.return_value = []
        mock_get_provider.return_value = mock_provider
        job = make_extraction_job(self.project, user=self.owner, status='pending')
        run_glossary_extraction_job(job.pk)
        strings_passed = mock_provider.extract_glossary.call_args[0][0]
        self.assertIn('submit', strings_passed)
        self.assertIn('cancel', strings_passed)

    @patch('api.verification_providers.get_verification_provider')
    def test_filters_out_malformed_suggestions(self, mock_get_provider):
        _make_ai_provider(self.project)
        lang = make_language(self.project, 'EN')
        _set_default_lang(lang)
        token = make_token(self.project, key='greeting')
        make_translation(token, lang, text='Hello')
        mock_provider = MagicMock()
        mock_provider.extract_glossary.return_value = [
            {'term': 'Good', 'definition': 'Fine', 'translations': []},
            {'definition': 'missing term key'},
            'not a dict at all',
            {'term': '', 'definition': 'empty term string'},
        ]
        mock_get_provider.return_value = mock_provider
        job = make_extraction_job(self.project, user=self.owner, status='pending')
        run_glossary_extraction_job(job.pk)
        job.refresh_from_db()
        self.assertEqual(len(job.suggestions), 1)
        self.assertEqual(job.suggestions[0]['term'], 'Good')

    @patch('api.verification_providers.get_verification_provider')
    def test_sets_completed_at_and_status_on_success(self, mock_get_provider):
        _make_ai_provider(self.project)
        lang = make_language(self.project, 'EN')
        _set_default_lang(lang)
        token = make_token(self.project, key='greeting')
        make_translation(token, lang, text='Hello')
        mock_provider = MagicMock()
        mock_provider.extract_glossary.return_value = []
        mock_get_provider.return_value = mock_provider
        job = make_extraction_job(self.project, user=self.owner, status='pending')
        run_glossary_extraction_job(job.pk)
        job.refresh_from_db()
        self.assertEqual(job.status, 'complete')
        self.assertIsNotNone(job.completed_at)


# ---------------------------------------------------------------------------
# api/tasks/verification.py
# ---------------------------------------------------------------------------

class RunVerificationJobTests(TestCase):

    def setUp(self):
        self.owner = make_user('owner')
        self.project = make_project(owner=self.owner)

    def _patch_dispatch(self):
        return patch('api.dispatcher.dispatch_event')

    def test_returns_early_for_nonexistent_report(self):
        with self._patch_dispatch():
            run_verification_job(999999)  # must not raise

    def test_fails_when_no_ai_provider(self):
        report = _make_report(self.project, self.owner)
        with self._patch_dispatch() as mock_dispatch:
            run_verification_job(report.pk)
        report.refresh_from_db()
        self.assertEqual(report.status, VerificationReport.Status.failed)
        self.assertIn('No AI provider', report.error_message)
        self.assertIsNotNone(report.completed_at)
        mock_dispatch.assert_called_once()

    def test_fails_when_no_strings_match(self):
        _make_ai_provider(self.project)
        report = _make_report(self.project, self.owner)
        with self._patch_dispatch() as mock_dispatch:
            run_verification_job(report.pk)
        report.refresh_from_db()
        self.assertEqual(report.status, VerificationReport.Status.failed)
        self.assertIn('No strings', report.error_message)
        mock_dispatch.assert_called_once()

    @patch('api.verification_providers.get_verification_provider')
    def test_source_quality_mode_completes(self, mock_get_provider):
        _make_ai_provider(self.project)
        lang = make_language(self.project, 'EN')
        _set_default_lang(lang)
        token = make_token(self.project, key='greeting')
        make_translation(token, lang, text='Hello')
        mock_provider = MagicMock()
        mock_provider.verify.return_value = [
            {'token_id': token.pk, 'plural_form': None,
             'severity': 'ok', 'suggestion': '', 'reason': ''},
        ]
        mock_get_provider.return_value = mock_provider
        report = _make_report(self.project, self.owner, mode='source_quality')
        with self._patch_dispatch():
            run_verification_job(report.pk)
        report.refresh_from_db()
        self.assertEqual(report.status, VerificationReport.Status.complete)
        self.assertIsNotNone(report.result)
        self.assertEqual(report.result['summary']['ok'], 1)
        self.assertEqual(report.result['summary']['total'], 1)
        self.assertIsNotNone(report.completed_at)

    @patch('api.verification_providers.get_verification_provider')
    def test_translation_accuracy_mode_completes(self, mock_get_provider):
        _make_ai_provider(self.project)
        src_lang = make_language(self.project, 'EN')
        tgt_lang = make_language(self.project, 'DE')
        token = make_token(self.project, key='greeting')
        make_translation(token, src_lang, text='Hello')
        make_translation(token, tgt_lang, text='Hallo')
        mock_provider = MagicMock()
        mock_provider.verify.return_value = [
            {'token_id': token.pk, 'plural_form': None,
             'severity': 'warning', 'suggestion': 'Hallo!', 'reason': 'punctuation'},
        ]
        mock_get_provider.return_value = mock_provider
        report = _make_report(
            self.project, self.owner,
            mode='translation_accuracy', target_language='DE',
        )
        with self._patch_dispatch():
            run_verification_job(report.pk)
        report.refresh_from_db()
        self.assertEqual(report.status, VerificationReport.Status.complete)
        self.assertEqual(report.result['summary']['warning'], 1)

    @patch('api.verification_providers.get_verification_provider')
    def test_fails_on_provider_error_and_fires_webhook(self, mock_get_provider):
        _make_ai_provider(self.project)
        lang = make_language(self.project, 'EN')
        _set_default_lang(lang)
        token = make_token(self.project, key='k')
        make_translation(token, lang, text='Hello')
        mock_provider = MagicMock()
        mock_provider.verify.side_effect = RuntimeError('API down')
        mock_get_provider.return_value = mock_provider
        report = _make_report(self.project, self.owner)
        with self._patch_dispatch() as mock_dispatch:
            run_verification_job(report.pk)
        report.refresh_from_db()
        self.assertEqual(report.status, VerificationReport.Status.failed)
        mock_dispatch.assert_called_once()

    @patch('api.verification_providers.get_verification_provider')
    def test_summary_counts_ok_warning_error(self, mock_get_provider):
        _make_ai_provider(self.project)
        lang = make_language(self.project, 'EN')
        _set_default_lang(lang)
        tokens = []
        for key in ('a', 'b', 'c'):
            t = make_token(self.project, key=key)
            make_translation(t, lang, text=f'Text {key}')
            tokens.append(t)
        mock_provider = MagicMock()
        mock_provider.verify.return_value = [
            {'token_id': tokens[0].pk, 'plural_form': None, 'severity': 'ok',      'suggestion': '', 'reason': ''},
            {'token_id': tokens[1].pk, 'plural_form': None, 'severity': 'warning',  'suggestion': '', 'reason': ''},
            {'token_id': tokens[2].pk, 'plural_form': None, 'severity': 'error',    'suggestion': '', 'reason': ''},
        ]
        mock_get_provider.return_value = mock_provider
        report = _make_report(self.project, self.owner)
        with self._patch_dispatch():
            run_verification_job(report.pk)
        report.refresh_from_db()
        summary = report.result['summary']
        self.assertEqual(summary['ok'],      1)
        self.assertEqual(summary['warning'], 1)
        self.assertEqual(summary['error'],   1)
        self.assertEqual(summary['total'],   3)

    @patch('api.verification_providers.get_verification_provider')
    def test_sets_string_count(self, mock_get_provider):
        _make_ai_provider(self.project)
        lang = make_language(self.project, 'EN')
        _set_default_lang(lang)
        for i in range(3):
            t = make_token(self.project, key=f'key{i}')
            make_translation(t, lang, text=f'Text {i}')
        mock_provider = MagicMock()
        mock_provider.verify.return_value = []
        mock_get_provider.return_value = mock_provider
        report = _make_report(self.project, self.owner)
        with self._patch_dispatch():
            run_verification_job(report.pk)
        report.refresh_from_db()
        self.assertEqual(report.string_count, 3)

    @patch('api.verification_providers.get_verification_provider')
    def test_batches_provider_calls_for_large_input(self, mock_get_provider):
        _make_ai_provider(self.project)
        lang = make_language(self.project, 'EN')
        _set_default_lang(lang)
        for i in range(25):
            t = make_token(self.project, key=f'key{i}')
            make_translation(t, lang, text=f'Text {i}')
        mock_provider = MagicMock()
        mock_provider.verify.return_value = []
        mock_get_provider.return_value = mock_provider
        report = _make_report(self.project, self.owner)
        with self._patch_dispatch():
            run_verification_job(report.pk)
        # 25 items with VERIFY_BATCH_SIZE=20 → 2 provider calls
        self.assertEqual(mock_provider.verify.call_count, 2)

    @patch('api.verification_providers.get_verification_provider')
    def test_enforce_cap_removes_oldest_reports(self, mock_get_provider):
        _make_ai_provider(self.project)
        lang = make_language(self.project, 'EN')
        _set_default_lang(lang)
        token = make_token(self.project, key='k')
        make_translation(token, lang, text='Hello')
        mock_provider = MagicMock()
        mock_provider.verify.return_value = [
            {'token_id': token.pk, 'plural_form': None,
             'severity': 'ok', 'suggestion': '', 'reason': ''},
        ]
        mock_get_provider.return_value = mock_provider
        self.project.verification_cap = 2
        self.project.save()
        for _ in range(3):
            VerificationReport.objects.create(
                project=self.project, created_by=self.owner,
                mode='source_quality', checks=['spelling_grammar'],
                status=VerificationReport.Status.complete,
            )
        report = _make_report(self.project, self.owner)
        with self._patch_dispatch():
            run_verification_job(report.pk)
        self.assertLessEqual(
            VerificationReport.objects.filter(project=self.project).count(), 2
        )

    @patch('api.verification_providers.get_verification_provider')
    def test_enriched_results_contain_token_key_and_language(self, mock_get_provider):
        _make_ai_provider(self.project)
        lang = make_language(self.project, 'EN')
        _set_default_lang(lang)
        token = make_token(self.project, key='hello_key')
        make_translation(token, lang, text='Hello')
        mock_provider = MagicMock()
        mock_provider.verify.return_value = [
            {'token_id': token.pk, 'plural_form': None,
             'severity': 'ok', 'suggestion': 'Hi', 'reason': 'shorter'},
        ]
        mock_get_provider.return_value = mock_provider
        report = _make_report(self.project, self.owner)
        with self._patch_dispatch():
            run_verification_job(report.pk)
        report.refresh_from_db()
        enriched = report.result['results']
        self.assertEqual(len(enriched), 1)
        self.assertEqual(enriched[0]['token_key'], 'hello_key')
        self.assertEqual(enriched[0]['language'], 'EN')
        self.assertEqual(enriched[0]['suggestion'], 'Hi')

    @patch('api.verification_providers.get_verification_provider')
    def test_fires_webhook_on_success(self, mock_get_provider):
        _make_ai_provider(self.project)
        lang = make_language(self.project, 'EN')
        _set_default_lang(lang)
        token = make_token(self.project, key='k')
        make_translation(token, lang, text='Hello')
        mock_provider = MagicMock()
        mock_provider.verify.return_value = []
        mock_get_provider.return_value = mock_provider
        report = _make_report(self.project, self.owner)
        with self._patch_dispatch() as mock_dispatch:
            run_verification_job(report.pk)
        mock_dispatch.assert_called_once()
        call_kwargs = mock_dispatch.call_args.kwargs
        self.assertEqual(call_kwargs['event_type'], 'verification.completed')
        self.assertEqual(call_kwargs['payload']['report_id'], report.pk)


# ---------------------------------------------------------------------------
# api/tasks/webhook.py
# ---------------------------------------------------------------------------

class SendWebhookTaskTests(TestCase):

    def setUp(self):
        self.user = make_user('owner')
        self.project = make_project(owner=self.user)

    def _make_endpoint(self, is_active=True, auth_token=None):
        endpoint = WebhookEndpoint.objects.create(
            project=self.project,
            title='Hook',
            url=encrypt('https://example.com/hook'),
            events=['translation.created'],
            is_active=is_active,
        )
        if auth_token:
            endpoint.auth_token = encrypt(auth_token)
            endpoint.save()
        return endpoint

    def _mock_urlopen(self):
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200
        return mock_resp

    def test_returns_early_for_nonexistent_endpoint(self):
        send_webhook(999999, 'translation.created', {})
        self.assertEqual(WebhookDeliveryLog.objects.count(), 0)

    def test_returns_early_for_inactive_endpoint(self):
        endpoint = self._make_endpoint(is_active=False)
        send_webhook(endpoint.pk, 'translation.created', {})
        self.assertEqual(WebhookDeliveryLog.objects.count(), 0)

    @patch('api.tasks.webhook.urllib.request.urlopen')
    def test_includes_bearer_auth_token_header(self, mock_urlopen):
        captured = {}

        def capture(req, timeout=None):
            captured['headers'] = dict(req.headers)
            return self._mock_urlopen()

        mock_urlopen.side_effect = capture
        endpoint = self._make_endpoint(auth_token='my-secret-token')

        with patch('socket.getaddrinfo', return_value=_PUBLIC_ADDR):
            send_webhook(endpoint.pk, 'translation.created', {'key': 'val'})

        auth = captured['headers'].get('Authorization')
        self.assertIsNotNone(auth)
        self.assertEqual(auth, 'Bearer my-secret-token')

    @patch('api.tasks.webhook.urllib.request.urlopen')
    def test_skips_auth_header_on_decrypt_failure(self, mock_urlopen):
        captured = {}

        def capture(req, timeout=None):
            captured['headers'] = dict(req.headers)
            return self._mock_urlopen()

        mock_urlopen.side_effect = capture
        endpoint = self._make_endpoint()
        # Store garbage bytes that will fail decryption
        WebhookEndpoint.objects.filter(pk=endpoint.pk).update(
            auth_token=b'not-valid-ciphertext'
        )

        with patch('socket.getaddrinfo', return_value=_PUBLIC_ADDR):
            send_webhook(endpoint.pk, 'translation.created', {'key': 'val'})

        # Delivery still happened; no Authorization header
        self.assertNotIn('Authorization', captured.get('headers', {}))
        log = WebhookDeliveryLog.objects.get(endpoint=endpoint)
        self.assertEqual(log.status_code, 200)
